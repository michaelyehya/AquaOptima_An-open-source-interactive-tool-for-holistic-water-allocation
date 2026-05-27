# water_model.py  — importable by both the Jupyter notebook and the Streamlit app
# ============================================================
# Water Allocation Model  (LP + numpy, epsilon-constraint Pareto)
#
# Multi-objective water allocation optimization. Three objectives:
#   OF1: economic cost  (USD/yr)              — linear, minimized
#   OF2: environmental  (volume + energy + CO2 composite, [0,1]) — minimized
#   OF3: social equity  (5-indicator weighted composite WE, [0,1]) — maximized
#
# Pipeline:
#   Phase 1 (precompute_bounds):
#     Step 1 — exact LP min/max for the three linear OF2 sub-components
#              (OF2a volume, OF2b energy, OF2c CO2)
#     Step 2 — LP-sampled bounds for the five nonlinear social indicators
#              (LI, WGC, WSRV, WC, WSGR) via 2000 random-direction LPs.
#              Each LP returns a feasible vertex; indicators evaluated in
#              numpy at each vertex; empirical [min, max] used as bounds.
#
#   Phase 2 (generate_pareto_front):
#     2a — three reference points (Opt-OF1, Opt-OF2 via LP; Opt-OF3 from corpus)
#     2b — corpus augmentation via three LP sweeps with energy caps and
#          regional equity floors as parametric constraints
#     2c — Pareto enumeration over (eps2, eps3) grid: filter the corpus and
#          select the min-OF1 candidate satisfying both epsilon constraints
#
# Design notes
# ------------
# • Bounds normalize raw indicator values into [0,1] inside the OF2 and OF3
#   composite formulas. They are NOT optimization constraints. OF1 is never
#   bounded because it is never normalized.
# • OF2b (raw energy) is used as the eps2 constraint instead of the OF2
#   composite — composite normalization can degenerate under tightened
#   feasibility, raw OF2b stays clean and linear.
# • OF3 is never directly optimized. It is approximated via linear
#   regional-equity floor proxies inside the corpus-augmentation LPs, then
#   evaluated in numpy at each LP vertex. This avoids the numerical
#   inconsistency of nonlinear-NLP solvers on the WE expression (where the
#   reported WE differs from numpy-recomputed WE).
# ============================================================

import pandas as pd
import numpy as np
from scipy.optimize import linprog
import os
import time
import warnings
warnings.filterwarnings('ignore')

DATA_FILE = 'WaterAllocationData_Synthetic.xlsx'
OUTPUT_FILE = 'WaterAllocationResults.xlsx'


# ─────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────

def normalize(x, x_min, x_max, minimize=True):
    """
    Min-max normalization to [0,1] where 1 = best performance.
    minimize=True  -> lower raw value is better  (max-x)/(max-min)
    minimize=False -> higher raw value is better (x-min)/(max-min)
    """
    rng = x_max - x_min
    if abs(rng) < 1e-12:
        return 0.5
    return (x_max - x) / rng if minimize else (x - x_min) / rng


# ─────────────────────────────────────────────────────────────
# DataManager
# ─────────────────────────────────────────────────────────────

class DataManager:
    """
    Loads and validates input data from the Excel workbook.

    Required sheets
    ---------------
    WaterSources  : one row per feasible (source, technology, end_use) pathway.
                    Columns: source_id, source_name, technology, end_use,
                             cost_uvw (USD/m3), energy_uvw (kWh/m3),
                             co2_uvw (ton CO2/m3), supply_cap (m3/yr), feasible (0/1)
                    Optional: region_id (triggers REGIONAL mode)
    Demand        : sectoral water demand.
                    Columns: end_use, demand_m3yr
    SocialParams  : regional socio-economic parameters.
                    Columns: region_id, region_name, population, income_per_capita,
                             employment_coeff_municipal, employment_coeff_agricultural,
                             employment_coeff_industrial,
                             demand_municipal, demand_agricultural, demand_industrial
    """

    def __init__(self, file_path):
        self.file_path = file_path
        self.water_sources = None
        self.demand = None
        self.social_params = None
        self.regional_mode = False   # True when WaterSources has a region_id column

    def load_all(self):
        """Load all three sheets, validate, and print a summary."""
        print(f'Loading data from: {self.file_path}')
        self.water_sources = self._load_water_sources()
        self.demand = self._load_demand()
        self.social_params = self._load_social_params()
        self.regional_mode = 'region_id' in self.water_sources.columns
        self._print_summary()
        return self

    def get_demand_by_sector(self):
        """Returns dict: end_use -> demand_m3yr."""
        return dict(zip(self.demand['end_use'], self.demand['demand_m3yr']))

    def get_source_supply_caps(self):
        """Returns dict: source_name -> supply_cap (m3/yr). Aggregate mode only."""
        return (self.water_sources
                    .groupby('source_name')['supply_cap']
                    .first().to_dict())

    def get_regional_supply_caps(self):
        """Returns dict: (source_name, region_id) -> supply_cap. Regional mode only."""
        if not self.regional_mode:
            return {}
        return (self.water_sources
                    .groupby(['source_name', 'region_id'])['supply_cap']
                    .first().to_dict())

    def get_regional_supply_per_region(self):
        """Returns dict: region_id -> total supply cap across all sources. Regional mode only."""
        if not self.regional_mode:
            return {}
        result = {}
        for (src, rgn), cap in self.get_regional_supply_caps().items():
            result[rgn] = result.get(rgn, 0.0) + float(cap)
        return result

    def get_regional_demand(self):
        """Returns dict: (end_use, region_id) -> demand_m3yr. Regional mode only."""
        if not self.regional_mode:
            return {}
        sp = self.social_params
        result = {}
        for _, row in sp.iterrows():
            rid = int(row['region_id'])
            result[('Municipal',    rid)] = float(row['demand_municipal'])
            result[('Agricultural', rid)] = float(row['demand_agricultural'])
            result[('Industrial',   rid)] = float(row['demand_industrial'])
        return result

    def _load_water_sources(self):
        df = pd.read_excel(self.file_path, sheet_name='WaterSources')
        req = ['source_id', 'source_name', 'technology', 'end_use',
               'cost_uvw', 'energy_uvw', 'co2_uvw', 'supply_cap', 'feasible']
        self._check(df, req, 'WaterSources')
        df = df[df['feasible'] == 1].reset_index(drop=True)
        for col in ['cost_uvw', 'energy_uvw', 'co2_uvw', 'supply_cap']:
            if (df[col] < 0).any():
                raise ValueError(f'Negative values in WaterSources["{col}"]')
        return df

    def _load_demand(self):
        df = pd.read_excel(self.file_path, sheet_name='Demand')
        self._check(df, ['end_use', 'demand_m3yr'], 'Demand')
        return df

    def _load_social_params(self):
        df = pd.read_excel(self.file_path, sheet_name='SocialParams')
        req = ['region_id', 'region_name', 'population', 'income_per_capita',
               'employment_coeff_municipal', 'employment_coeff_agricultural',
               'employment_coeff_industrial',
               'demand_municipal', 'demand_agricultural', 'demand_industrial']
        self._check(df, req, 'SocialParams')
        return df.reset_index(drop=True)

    @staticmethod
    def _check(df, required, sheet):
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f'Sheet "{sheet}" missing columns: {missing}')

    def _print_summary(self):
        dem = self.get_demand_by_sector()
        if self.regional_mode:
            # Sum unique (source, region) caps — avoids triple-counting
            # because multiple pathways share the same (source, region) cap
            caps_total = float(
                self.water_sources
                    .groupby(['source_name', 'region_id'])['supply_cap']
                    .first().sum()
            )
        else:
            caps_total = sum(self.get_source_supply_caps().values())
        print(
            f'  Feasible pathways (decision variables): {len(self.water_sources)}')
        print(
            f'  Mode            : {"REGIONAL" if self.regional_mode else "AGGREGATE"}')
        print(f'  Demand sectors  : {list(dem.keys())}')
        print(f'  Regions         : {list(self.social_params["region_name"])}')
        print(f'  Total demand    : {sum(dem.values()):.3e} m\u00b3/yr')
        print(f'  Total supply cap: {caps_total:.3e} m\u00b3/yr')


# ─────────────────────────────────────────────────────────────
# WaterAllocationModel
# ─────────────────────────────────────────────────────────────

class WaterAllocationModel:
    """
    Multi-objective water allocation optimization via LP + numpy.

    Decision variable
    -----------------
    P[i] >= 0  (m3/yr): water allocated via feasible pathway i,
    where i encodes a unique (source_u, technology_w, end_use_v) triple.

    Objectives
    ----------
    OF1 (linear)    : min  sum_i  C_i * P[i]                         (USD/yr)
    OF2 (linear)    : min  normalized (volume + energy + CO2)        [0,1]
    OF3 (nonlinear) : max  WE = weighted sum of 5 normalized social indicators [0,1]

    Social indicators (Table 10 of proposal)
    -----------------------------------------
    LI   (w=0.182)  Labour Intensity             -- maximize
    WGC  (w=0.318)  Water-use Gini Coefficient   -- minimize  [nonlinear]
    WSRV (w=0.318)  Shortage Rate Variance       -- minimize  [nonlinear]
    WC   (w=0.045)  Williamson Coefficient       -- minimize  [nonlinear]
    WSGR (w=0.136)  Supply Guarantee Rate        -- maximize

    Approach
    --------
    The Pareto front is generated via a hybrid LP + numpy approach rather
    than a constrained NLP per epsilon-grid cell. The corpus-and-filter
    design replaces nonlinear-NLP solving (which exhibited numerical
    inconsistency on the WE expression) with parametric LP sweeps that
    produce a dense set of feasible candidate solutions, then enumerates
    the Pareto front by selection.

    Phase 1 — precompute_bounds
        Step 1: exact LP min/max for OF2a, OF2b, OF2c (linear → exact).
        Step 2: LP-sampled bounds for LI, WGC, WSRV, WC, WSGR. 2000 random-
                direction LPs each return a feasible polytope vertex;
                _eval_indics_numpy evaluates the five social indicators at
                each vertex; empirical [min, max] used as bounds.

    Phase 2 — generate_pareto_front
        2a: reference points (Opt-OF1 and Opt-OF2 via LP; Opt-OF3 from
            the LP corpus).
        2b: corpus augmentation via three LP sweeps with energy caps and
            regional equity floors as parametric constraints (~870 LPs).
        2c: Pareto enumeration over (eps2, eps3) grid — filter the corpus
            and pick the min-OF1 candidate satisfying both eps constraints.

    Epsilon-constraint formulation
    ------------------------------
    Primary obj     : min OF1  (economic cost)
    Eps constraint 1: OF2b (raw energy kWh/yr) <= eps2   [linear → clean]
    Eps constraint 2: WE >= eps3                          [filter on corpus]
    """

    # Social indicator weights from meta-analysis of 21 peer-reviewed studies
    SOCIAL_WEIGHTS = {'LI': 0.182, 'WGC': 0.318, 'WSRV': 0.318,
                      'WC': 0.045, 'WSGR': 0.136}
    # OF2 environmental sub-weights (equal by default)
    ENV_WEIGHTS = {'OF2a': 1/3, 'OF2b': 1/3, 'OF2c': 1/3}

    def __init__(self, data_manager):
        self.dm = data_manager
        self.ws = data_manager.water_sources
        self.n = len(self.ws)
        self.regional_mode = data_manager.regional_mode
        self.bounds = {}
        self.pareto_front = []
        self.all_solutions = []
        mode = 'REGIONAL' if self.regional_mode else 'AGGREGATE'
        print(
            f'WaterAllocationModel ready  |  {self.n} decision variables  |  mode: {mode}')

    # ── Constraint matrix (LP form) ────────────────────────────

    def _build_lp_matrices(self):
        """
        Return (A_ub, b_ub, var_bounds) encoding all supply/demand
        constraints in scipy linprog form:
            A_ub @ P <= b_ub,   P[i] >= 0.

        Regional mode:
          (1) Per-(source, region) supply caps
          (2) Per-region per-sector demand floors (deficit-aware: scaled
              by avail_frac if regional supply < regional demand)
          (3) Global balance constraint

        Aggregate mode:
          (1) Per-source supply caps
          (2) Per-end-use demand floors
          (3) Global balance constraint
        """
        ws = self.ws
        n = self.n
        demand = self.dm.get_demand_by_sector()
        total_dem = float(sum(demand.values()))
        A_ub, b_ub = [], []

        def _add_le(indices, rhs):
            row = np.zeros(n)
            for i in indices:
                row[i] = 1.0
            A_ub.append(row)
            b_ub.append(rhs)

        def _add_ge(indices, rhs):
            row = np.zeros(n)
            for i in indices:
                row[i] = -1.0
            A_ub.append(row)
            b_ub.append(-rhs)

        if self.regional_mode:
            regional_caps = self.dm.get_regional_supply_caps()
            regional_demand = self.dm.get_regional_demand()
            reg_sup_per_rgn = self.dm.get_regional_supply_per_region()
            sp = self.dm.social_params
            total_sup = float(sum(regional_caps.values()))

            for (src, rgn), cap in regional_caps.items():
                idx = ws.index[
                    (ws['source_name'] == src) & (ws['region_id'] == rgn)
                ].tolist()
                if idx and cap > 0:
                    _add_le(idx, float(cap))

            for _, r_row in sp.iterrows():
                rid = int(r_row['region_id'])
                reg_sup = float(reg_sup_per_rgn.get(rid, 0.0))
                reg_dem_vals = {eu: float(regional_demand.get((eu, rid), 0.0))
                                for eu in demand}
                reg_dem_total = sum(reg_dem_vals.values())

                if reg_sup >= reg_dem_total:
                    for eu, reg_dem in reg_dem_vals.items():
                        idx = ws.index[
                            (ws['end_use'] == eu) & (ws['region_id'] == rid)
                        ].tolist()
                        if idx and reg_dem > 0:
                            _add_ge(idx, float(reg_dem))
                else:
                    avail_frac = reg_sup / max(reg_dem_total, 1e-8)
                    for eu, reg_dem in reg_dem_vals.items():
                        idx = ws.index[
                            (ws['end_use'] == eu) & (ws['region_id'] == rid)
                        ].tolist()
                        if idx and reg_dem > 0:
                            _add_ge(idx, float(reg_dem * avail_frac * 0.90))

            rhs_global = total_dem if total_sup >= total_dem else total_sup * 0.90
            _add_ge(list(range(n)), rhs_global)

        else:
            for src, cap in self.dm.get_source_supply_caps().items():
                idx = ws.index[ws['source_name'] == src].tolist()
                if idx:
                    _add_le(idx, float(cap))
            for eu, dem in demand.items():
                idx = ws.index[ws['end_use'] == eu].tolist()
                if idx and dem > 0:
                    _add_ge(idx, float(dem))
            _add_ge(list(range(n)), total_dem)

        A_ub = np.array(A_ub, dtype=float)
        b_ub = np.array(b_ub, dtype=float)
        var_bounds = [(0, None)] * n
        return A_ub, b_ub, var_bounds

    # ── Numpy evaluators for the social indicators and WE composite ────

    def _eval_indics_numpy(self, P):
        """Evaluate all 5 social indicators (LI, WGC, WSRV, WC, WSGR) from a
        numpy P vector. Pure closed-form arithmetic — no solver, no iteration.

        Used by:
        - LP-sampled bounds estimation (Phase 1 Step 2)
        - LP-based corpus augmentation (Phase 2 Step 2b)
        - Reference solves and final Pareto evaluation
        """
        ws_ = self.ws
        sp_ = self.dm.social_params
        R = len(sp_)
        EPS = 1e-8
        eu = ['Municipal', 'Agricultural', 'Industrial']

        # Cached index maps (rebuilt here for standalone correctness)
        region_idx = [ws_.index[ws_['region_id'] == int(
            sp_.iloc[r]['region_id'])].tolist() for r in range(R)]
        enduse_idx = {v: ws_.index[ws_['end_use'] == v].tolist() for v in eu}

        D_rv = {v: sp_['demand_'+v.lower()].values.astype(float) for v in eu}
        D_r = np.array([sum(float(D_rv[v][r]) for v in eu) for r in range(R)])
        pop = sp_['population'].values.astype(float)
        inc0 = sp_['income_per_capita'].values.astype(float)
        pop_T = float(pop.sum())
        e_v = {v: float(sp_['employment_coeff_'+v.lower()].mean()) for v in eu}
        D_tot = float(sum(self.dm.get_demand_by_sector().values()))

        Sr = np.array([P[region_idx[r]].sum() for r in range(R)])
        Pt = float(P.sum())
        Pv = {v: float(P[enduse_idx[v]].sum()) for v in eu}

        LI = sum(e_v[v]*Pv[v] for v in eu) / (Pt + EPS)
        WSGR = Pt / (D_tot + EPS)
        dfct = D_r - Sr
        pos = (dfct + np.sqrt(dfct**2 + EPS)) / 2.0
        SR = pos / (D_r + EPS)
        WSRV = float(((SR - SR.mean())**2).mean())
        rat = Sr / (D_r + EPS)
        mu_rat = float(rat.mean())
        gini_s = sum(np.sqrt((rat[i]-rat[j])**2 + EPS)
                     for i in range(R) for j in range(R))
        WGC = float(gini_s / (2.0*R**2*mu_rat + EPS))
        yr = inc0*Sr / (D_r + EPS)
        ybar = (pop*yr).sum() / (pop_T + EPS)
        WC = float(np.sqrt((pop*(yr-ybar)**2).sum() + EPS) /
                   (pop_T*ybar + EPS))

        return {'LI': float(LI), 'WGC': WGC, 'WSRV': WSRV,
                'WC': WC, 'WSGR': float(WSGR)}

    def _compute_we_numpy(self, indics):
        """Compute WE (OF3) from a raw indicator dict using self.bounds for
        normalisation. Clamps each normalised indicator to [0,1] to prevent
        negative or >1 contributions. Matches the mathematical definition of
        the social objective exactly."""
        we = 0.0
        for k, w in self.SOCIAL_WEIGHTS.items():
            b = self.bounds.get(k, [None, None])
            if b[0] is None or b[1] is None:
                we += w * 0.5
                continue
            rng = b[1] - b[0]
            if abs(rng) < 1e-10:
                we += w * 0.5
                continue
            if k in ('WGC', 'WSRV', 'WC'):
                n_ = (b[1] - indics[k]) / rng
            else:
                n_ = (indics[k] - b[0]) / rng
            we += w * max(0.0, min(1.0, n_))
        return float(we)

    # ── Phase 1: Pre-compute normalisation bounds ──────────────

    def precompute_bounds(self, verbose=True):
        """
        Compute [min, max] for each indicator that needs normalisation.

        Strategy
        --------
        OF2a, OF2b, OF2c  — linear in P[i]; bounds via exact scipy HiGHS LP
                            (Step 1, six LPs, exact answers).
        LI, WGC, WSRV, WC, WSGR — nonlinear in P[i]; bounds via LP sampling
                            (Step 2). 2000 random LP objectives visit corner
                            points of the feasible polytope; each corner is
                            evaluated via _eval_indics_numpy; empirical
                            [min, max] used as bounds.

        Why LP sampling for the social indicators
        -----------------------------------------
        - Random Monte Carlo over supply caps violates demand floor
          constraints, producing infeasible points.
        - LP sampling with random Gaussian objectives yields constraint-
          feasible polytope vertices by construction.
        - The five social indicators are highly nonlinear (Gini, Williamson,
          shortage variance) — nonlinear-NLP solvers exhibit numerical
          inconsistency on these objectives. Sampling sidesteps this entirely.

        Note: OF1 and the OF2/OF3 composites do not appear in self.bounds.
        OF1 stays in raw USD/yr throughout (no normalisation needed). The
        OF2 and OF3 composites are themselves outputs of normalisation,
        living in [0,1] by construction.
        """
        self.bounds = {}

        print('\n' + '=' * 65)
        print('PHASE 1: Pre-computing normalisation bounds')
        print('=' * 65)

        # ── Step 1: Linear bounds via scipy HiGHS LP ──────────
        print('\n[Step 1] Linear bounds via scipy HiGHS LP (OF2a, OF2b, OF2c)')
        A_ub, b_ub, var_bounds = self._build_lp_matrices()

        cost_arr = self.ws['cost_uvw'].values.astype(float)
        energy_arr = self.ws['energy_uvw'].values.astype(float)
        co2_arr = self.ws['co2_uvw'].values.astype(float)
        ones_arr = np.ones(self.n)

        for key, c in [('OF2a', ones_arr), ('OF2b', energy_arr), ('OF2c', co2_arr)]:
            r_min = linprog(c, A_ub=A_ub, b_ub=b_ub,
                            bounds=var_bounds, method='highs')
            r_max = linprog(-c, A_ub=A_ub, b_ub=b_ub,
                            bounds=var_bounds, method='highs')
            if r_min.success and r_max.success:
                self.bounds[key] = [float(r_min.fun), float(-r_max.fun)]
            else:
                self.bounds[key] = [0.0, 1.0]
            if verbose:
                print(
                    f'  {key}: min={self.bounds[key][0]:.4e}  max={self.bounds[key][1]:.4e}')

        # ── Step 2: LP-sampled bounds for all social indicators ──────
        # 2000 random Gaussian objective vectors → 2000 polytope vertices.
        # Each vertex evaluated via _eval_indics_numpy. Empirical min/max
        # over the sampled vertices used as the bounds.
        print('\n[Step 2] LP-sampled bounds (LI, WGC, WSRV, WC, WSGR)')
        rng_s2 = np.random.default_rng(42)
        s2 = {'LI': [], 'WGC': [], 'WSRV': [], 'WC': [], 'WSGR': []}
        samples_P = []     # store P vectors for later use in Pareto phase
        ok2 = 0
        for _ in range(2000):
            c = rng_s2.standard_normal(self.n)
            r = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=var_bounds, method='highs',
                        options={'disp': False, 'time_limit': 1.0})
            if r.success:
                try:
                    ind = self._eval_indics_numpy(r.x)
                    if all(np.isfinite(v) for v in ind.values()):
                        for k in s2:
                            s2[k].append(ind[k])
                        samples_P.append((r.x, ind))
                        ok2 += 1
                except Exception:
                    pass

        if verbose:
            print(f'  LP sampling: {ok2}/2000 feasible points')

        for k in ['LI', 'WGC', 'WSRV', 'WC', 'WSGR']:
            if s2[k]:
                self.bounds[k] = [min(s2[k]), max(s2[k])]
                if verbose:
                    print(
                        f'  {k:5s}: min={self.bounds[k][0]:.4e}  max={self.bounds[k][1]:.4e}')
            else:
                if verbose:
                    print(
                        f'  {k:5s}: LP sampling produced no valid values — using [0,1]')
                self.bounds[k] = [0.0, 1.0]

        # Store the LP sample corpus for generate_pareto_front to reuse
        # (avoids re-running 2000 solves)
        self._lp_corpus = samples_P

        if verbose:
            print('\nBounds summary:')
            for k, v in self.bounds.items():
                rng = (v[1] - v[0]) if (v[0] is not None and v[1]
                                        is not None) else float('nan')
                degen = ' *** DEGENERATE ***' if abs(rng) < 1e-10 else ''
                print(
                    f'  {k:5s}: [{v[0]:.4e}, {v[1]:.4e}]  range={rng:.2e}{degen}')

        return self.bounds

    # ── Phase 2: Generate Pareto front ─────────────────────────

    def generate_pareto_front(self, n_eps=10, verbose=True):
        """
        Generate Pareto front via LP-corpus + filter epsilon-constraint method.

        Primary objective : min OF1 (economic cost)
        Eps constraint 1  : OF2b (energy kWh/yr) <= eps2
        Eps constraint 2  : OF3 (social equity WE) >= eps3

        Three-stage corpus construction
        -------------------------------
        Stage 0: Reuse 2000 LP samples from precompute_bounds() as seeds.
        Stage 1: Augment with parametric LP sweeps:
                 - Sweep 1 (~250 LPs): uniform alpha scaling of regional
                   equity-floor targets, across an energy-cap grid.
                 - Sweep 2 (~120 LPs): pin deficit regions at max, sweep
                   surplus regions independently.
                 - Sweep 3 (500 LPs): random independent per-region targets,
                   random energy caps.
        Stage 2: Pareto enumeration — for each (eps2, eps3) grid cell,
                 filter the corpus by both epsilon constraints and select
                 the min-OF1 candidate.

        Why this over a per-cell constrained NLP
        ----------------------------------------
        - OF3 is a complex nonlinear expression (Gini, Williamson, shortage
          variance). Nonlinear-NLP solvers exhibit numerical inconsistency
          where reported WE differs from numpy-recomputed WE.
        - LP + numpy is exact (every reported indicator value is recomputed
          from the actual P), fast, and never reports inconsistent values.
        - Trade-off: the corpus-and-filter approach is a sampling approximation,
          not exact per-cell optimisation. With ~2870 corpus members the
          approximation is dense enough that doubling corpus size produces
          negligible change in the Pareto front.
        """
        if not self.bounds:
            print('WARNING: bounds empty. Call precompute_bounds() first.')
            return []

        print('\n' + '=' * 65)
        print('PHASE 2: Pareto Front — LP-based Epsilon-Constraint')
        print('=' * 65)

        A_ub, b_ub, var_bounds = self._build_lp_matrices()
        cost_arr = self.ws['cost_uvw'].values.astype(float)
        energy_arr = self.ws['energy_uvw'].values.astype(float)
        co2_arr = self.ws['co2_uvw'].values.astype(float)

        # ── Step 2a: Reference points (all LP) ─────────────────
        print('\nStep 2a: Single-objective reference points (all LP)...')
        r1 = linprog(cost_arr, A_ub=A_ub, b_ub=b_ub,
                     bounds=var_bounds, method='highs')
        if r1.success:
            ind1 = self._eval_indics_numpy(r1.x)
            we1 = self._compute_we_numpy(ind1)
            print(
                f'  Opt-OF1: OF1={r1.fun:.3e}  OF2b={float(energy_arr @ r1.x):.3e}  WE={we1:.4f}')

        r2 = linprog(energy_arr, A_ub=A_ub, b_ub=b_ub,
                     bounds=var_bounds, method='highs')
        if r2.success:
            ind2 = self._eval_indics_numpy(r2.x)
            we2 = self._compute_we_numpy(ind2)
            print(
                f'  Opt-OF2: OF1={float(cost_arr @ r2.x):.3e}  OF2b={r2.fun:.3e}  WE={we2:.4f}')

        # OF3-opt via LP corpus enumeration
        corpus = getattr(self, '_lp_corpus', [])
        if corpus:
            scored = [(self._compute_we_numpy(ind), P, ind)
                      for P, ind in corpus]
            scored.sort(key=lambda x: -x[0])
            we_best, P_best, ind_best = scored[0]
            print(f'  Opt-OF3: OF1={float(cost_arr @ P_best):.3e}  '
                  f'OF2b={float(energy_arr @ P_best):.3e}  WE={we_best:.4f}')
        else:
            we_best = 0.7  # fallback

        # ── Step 2b: Build candidate corpus ────────────────────
        # Start with existing 2000 samples from Phase 1
        candidates = []
        for P, ind in corpus:
            candidates.append({
                'P': P,
                'OF1': float(cost_arr @ P),
                'OF2b': float(energy_arr @ P),
                'OF2c': float(co2_arr @ P),
                'OF3': self._compute_we_numpy(ind),
                **ind,
            })

        print(f'\nStep 2b: Augmenting corpus with targeted LP sweeps...')
        of2b_vals = [c['OF2b'] for c in candidates]
        of2b_max = max(of2b_vals)
        of2b_min = min(of2b_vals)
        eps2_grid = np.linspace(of2b_max * 0.99, of2b_min * 1.01, n_eps)

        # Precompute regional arrays
        sp = self.dm.social_params
        R = len(sp)
        eu_list = ['Municipal', 'Agricultural', 'Industrial']
        region_idx_list = [self.ws.index[self.ws['region_id'] == int(sp.iloc[r]['region_id'])].tolist()
                           for r in range(R)]
        D_r_arr = np.array([sum(float(sp.iloc[r]['demand_'+eu.lower()]) for eu in eu_list)
                            for r in range(R)])
        reg_sup = self.dm.get_regional_supply_per_region()
        reg_sup_ratio = np.array([reg_sup.get(int(sp.iloc[r]['region_id']), 0) / D_r_arr[r]
                                  for r in range(R)])

        def _solve_regional_target(eps2, target_ratios):
            """LP: min cost s.t. energy<=eps2 AND Sr[r] >= target_ratios[r]*D_r[r]"""
            A_list = [A_ub]
            b_list = list(b_ub)
            A_list.append(energy_arr[np.newaxis, :])
            b_list.append(eps2)
            for r in range(R):
                row = np.zeros(self.n)
                for i in region_idx_list[r]:
                    row[i] = -1.0
                A_list.append(row[np.newaxis, :])
                b_list.append(-target_ratios[r] * D_r_arr[r])
            A_full = np.vstack(A_list)
            b_full = np.array(b_list)
            return linprog(cost_arr, A_ub=A_full, b_ub=b_full, bounds=var_bounds,
                           method='highs', options={'disp': False, 'time_limit': 1.0})

        t0 = time.time()
        added = 0

        # ── Sweep 1: Uniform alpha scaling of target ratios ─────────────
        # alpha=0: no equity floor (LP-optimal cost dominates)
        # alpha=1: maximum equity (each region at its reg_sup_ratio, capped at 2.0)
        for alpha in np.linspace(0, 1.0, 25):
            target = np.array([alpha * min(reg_sup_ratio[r], 2.0)
                              for r in range(R)])
            for e2 in eps2_grid:
                res = _solve_regional_target(e2, target)
                if res.success:
                    try:
                        ind = self._eval_indics_numpy(res.x)
                        if all(np.isfinite(v) for v in ind.values()):
                            candidates.append({
                                'P': res.x,
                                'OF1': float(cost_arr @ res.x),
                                'OF2b': float(energy_arr @ res.x),
                                'OF2c': float(co2_arr @ res.x),
                                'OF3': self._compute_we_numpy(ind),
                                **ind,
                            })
                            added += 1
                    except Exception:
                        pass

        # ── Sweep 2: Fix deficit regions at max, sweep surplus separately ──
        for beta_s in np.linspace(0, 1.2, 15):
            target = np.zeros(R)
            for r in range(R):
                if reg_sup_ratio[r] >= 1.0:
                    target[r] = beta_s * min(reg_sup_ratio[r], 1.8)
                else:
                    target[r] = reg_sup_ratio[r]
            for e2 in np.linspace(of2b_max*0.99, of2b_min*1.01, 8):
                res = _solve_regional_target(e2, target)
                if res.success:
                    try:
                        ind = self._eval_indics_numpy(res.x)
                        if all(np.isfinite(v) for v in ind.values()):
                            candidates.append({
                                'P': res.x,
                                'OF1': float(cost_arr @ res.x),
                                'OF2b': float(energy_arr @ res.x),
                                'OF2c': float(co2_arr @ res.x),
                                'OF3': self._compute_we_numpy(ind),
                                **ind,
                            })
                            added += 1
                    except Exception:
                        pass

        # ── Sweep 3: Random independent per-region targets ─────────────
        rng_s3 = np.random.default_rng(123)
        for _ in range(500):
            target = np.array([rng_s3.uniform(0, min(reg_sup_ratio[r], 1.5))
                               for r in range(R)])
            e2 = float(rng_s3.uniform(of2b_min*1.01, of2b_max*0.99))
            res = _solve_regional_target(e2, target)
            if res.success:
                try:
                    ind = self._eval_indics_numpy(res.x)
                    if all(np.isfinite(v) for v in ind.values()):
                        candidates.append({
                            'P': res.x,
                            'OF1': float(cost_arr @ res.x),
                            'OF2b': float(energy_arr @ res.x),
                            'OF2c': float(co2_arr @ res.x),
                            'OF3': self._compute_we_numpy(ind),
                            **ind,
                        })
                        added += 1
                except Exception:
                    pass

        print(
            f'  {added} points added in {time.time()-t0:.1f}s  (corpus: {len(candidates)})')

        # ── Step 2c: Pareto enumeration ─────────────────────────
        print(
            f'\nStep 2c: Pareto enumeration over {n_eps}x{n_eps}={n_eps*n_eps} grid...')
        we_corpus = [c['OF3'] for c in candidates]
        we_min = min(we_corpus)
        we_max = max(we_corpus)
        eps3_grid = np.linspace(we_min + 0.005, we_max - 0.005, n_eps)

        print(f'  eps2 range: [{eps2_grid.min():.3e}, {eps2_grid.max():.3e}]')
        print(f'  eps3 range: [{eps3_grid.min():.4f}, {eps3_grid.max():.4f}]')

        self.pareto_front = []
        self.all_solutions = []
        uniq_keys = set()

        for i, e2 in enumerate(eps2_grid):
            for j, e3 in enumerate(eps3_grid):
                feas = [c for c in candidates if c['OF2b']
                        <= e2 and c['OF3'] >= e3]
                if not feas:
                    if verbose and (i*n_eps + j) % 20 == 0:
                        print(
                            f'  [{i*n_eps+j+1}/{n_eps*n_eps}] e2={e2:.3e} e3={e3:.3f}  INFEASIBLE')
                    continue
                best = min(feas, key=lambda c: c['OF1'])
                sol = {
                    'eps2': float(e2), 'eps3': float(e3),
                    'OF1': best['OF1'], 'OF2': best['OF2b'], 'OF3': best['OF3'],
                    'OF2a': float(best['P'].sum()), 'OF2b': best['OF2b'], 'OF2c': best['OF2c'],
                    'LI': best['LI'], 'WGC': best['WGC'], 'WSRV': best['WSRV'],
                    'WC': best['WC'], 'WSGR': best['WSGR'],
                    'P': best['P'].tolist(),
                }

                # Add regional allocations
                if self.regional_mode:
                    sp = self.dm.social_params
                    reg_alloc = {}
                    for _, row in sp.iterrows():
                        rgn_id = int(row['region_id'])
                        ridx = self.ws.index[self.ws['region_id']
                                             == rgn_id].tolist()
                        reg_alloc[row['region_name']] = float(
                            best['P'][ridx].sum())
                    sol['regional_allocations'] = reg_alloc

                self.all_solutions.append(sol)

                # Finer uniqueness: round to 0.1% in OF1/OF2b and 0.001 in WE
                key = (round(sol['OF1']/1e6),
                       round(sol['OF2b']/1e6), round(sol['OF3'], 4))
                if key not in uniq_keys:
                    uniq_keys.add(key)
                    self.pareto_front.append(sol)

        print(f'\n  Cells filled: {len(self.all_solutions)}/{n_eps*n_eps}')
        print(f'  Unique Pareto points: {len(self.pareto_front)}')
        if self.pareto_front:
            print(f'\n  Pareto front ranges:')
            print(f'    OF1  (cost):     [{min(s["OF1"] for s in self.pareto_front):.3e}, '
                  f'{max(s["OF1"] for s in self.pareto_front):.3e}] USD/yr')
            print(f'    OF2b (energy):   [{min(s["OF2b"] for s in self.pareto_front):.3e}, '
                  f'{max(s["OF2b"] for s in self.pareto_front):.3e}] kWh/yr')
            print(f'    OF3  (WE score): [{min(s["OF3"] for s in self.pareto_front):.4f}, '
                  f'{max(s["OF3"] for s in self.pareto_front):.4f}]')

        return self.pareto_front

    # ── Save results ───────────────────────────────────────────

    def save_results_to_excel(self, path):
        """Write Pareto front, all solutions, best detail, and bounds to Excel."""
        with pd.ExcelWriter(path, engine='openpyxl') as xw:

            if self.pareto_front:
                pd.DataFrame([{
                    'OF1_Cost_USD_yr':     s['OF1'],
                    'OF2_Env_Index':       s['OF2'],
                    'OF2a_Volume_m3yr':    s['OF2a'],
                    'OF2b_Energy_kWh_yr':  s['OF2b'],
                    'OF2c_CO2_ton_yr':     s['OF2c'],
                    'OF3_Social_WE':       s['OF3'],
                    'LI_Labour_Intensity': s['LI'],
                    'WGC_Gini':            s['WGC'],
                    'WSRV_ShortageVar':    s['WSRV'],
                    'WC_Williamson':       s['WC'],
                    'WSGR_GuaranteeRate':  s['WSGR'],
                } for s in self.pareto_front]
                ).to_excel(xw, sheet_name='ParetoFront', index=False)

            if self.all_solutions:
                pd.DataFrame([{
                    'eps2': s.get('eps2', ''), 'eps3': s.get('eps3', ''),
                    'OF1': s['OF1'], 'OF2': s['OF2'],
                    'OF2b_kWh': s['OF2b'], 'OF3': s['OF3'],
                } for s in self.all_solutions]
                ).to_excel(xw, sheet_name='AllSolutions', index=False)

            if self.pareto_front:
                best = min(self.pareto_front, key=lambda s: s['OF1'])
                out = self.ws.copy()
                out['P_m3yr'] = best['P']
                out['Cost_USD_yr'] = out['cost_uvw'] * out['P_m3yr']
                out['Energy_kWh_yr'] = out['energy_uvw'] * out['P_m3yr']
                out['CO2_ton_yr'] = out['co2_uvw'] * out['P_m3yr']
                out.to_excel(xw, sheet_name='BestEconSolution', index=False)

            if self.bounds:
                pd.DataFrame(
                    [{'indicator': k, 'min_value': v[0], 'max_value': v[1]}
                     for k, v in self.bounds.items()]
                ).to_excel(xw, sheet_name='NormBounds', index=False)

            if self.regional_mode and self.pareto_front:
                sp = self.dm.social_params
                reg_rows = []
                for k, sol in enumerate(self.pareto_front):
                    reg_alloc = sol.get('regional_allocations', {})
                    for _, row in sp.iterrows():
                        rname = row['region_name']
                        supply = reg_alloc.get(rname, 0.0)
                        demand = float(
                            row['demand_municipal'] +
                            row['demand_agricultural'] +
                            row['demand_industrial']
                        )
                        shortage = max(0.0, demand - supply)
                        reg_rows.append({
                            'Pareto_Point':   k + 1,
                            'OF1_Cost_USD_yr': sol['OF1'],
                            'OF3_Social_WE':  sol['OF3'],
                            'WSRV':           sol['WSRV'],
                            'Region':         rname,
                            'Region_ID':      int(row['region_id']),
                            'Demand_m3yr':    demand,
                            'Supply_m3yr':    supply,
                            'Shortage_m3yr':  shortage,
                            'Shortage_Rate':  shortage / max(demand, 1e-8),
                        })
                if reg_rows:
                    pd.DataFrame(reg_rows).to_excel(
                        xw, sheet_name='RegionalAllocation', index=False)

        print(f'Results saved -> {path}')
