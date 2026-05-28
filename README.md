# AquaOptima: An open-source interactive tool for holistic water allocation
AquaOptima: An open-source interactive tool for holistic water allocation under competing economic, environmental, and social objectives
## Overview

AquaOptima decides how much water to route through each **pathway** P[i], a unique combination of *source × treatment technology × end-use* — across multiple regions, in order to balance three competing objectives:

| Objective | Meaning | Type | Direction |

| **OF1** | Total economic cost (USD/yr) | Linear | Minimize |
| **OF2** | Environmental impact (water volume + energy + CO₂) | Linear | Minimize |
| **OF3** | Social equity — Water Equity index *WE* | Nonlinear | Maximize |

There is no single best answer: cheap allocations tend to be carbon-heavy or inequitable, and equitable ones tend to be expensive. Rather than one solution, AquaOptima returns a **Pareto front** of non-dominated allocations. Every point is optimal in the sense that no objective can improve without another worsening. Decision-makers then choose the point matching their priorities.

The repository ships with a synthetic three-region demo dataset so the model can be run and explored out of the box.

**Key features**

**Three competing objectives** — cost, environment, and a five-indicator social-equity composite (Labour Intensity, Water Gini Coefficient, Shortage Rate Variance, Williamson Coefficient, Supply Guarantee Rate).
 **Pareto-front output** via the epsilon-constraint method, not a single weighted answer.
 **Hybrid LP + NumPy engine** — fast, fully deterministic, and exact (see *Methodology*).
 **Fully data-driven** — switch case studies by pointing the model at a different Excel workbook with the same schema; no code changes.
 **Two front-ends** — a Jupyter notebook for development and a Streamlit GUI for non-coders, both running the same engine.

## Methodology

OF1 and OF2 are exactly linear in the decision variables, and OF3's nonlinearity is handled by decomposition rather than a nonlinear solver. The model runs in two phases:

- **Phase 1 — normalization bounds.** Six exact LPs fix the OF2 component ranges; ~2000 LP-sampled feasible vertices (a Monte Carlo step) map the ranges of the five social indicators so they can be normalized onto a common scale.
- **Phase 2 — Pareto front.** A corpus-and-filter epsilon-constraint sweep over a 10×10 grid. Candidate allocations are generated with SciPy's `linprog` (HiGHS), and the true OF3 is evaluated in closed form with NumPy at each candidate.

This replaced an earlier GEKKO/IPOPT nonlinear formulation. The LP + NumPy approach is faster (~2 ms per LP vs 200 ms–2 s per NLP), fully deterministic, and evaluates OF3 exactly with no solver drift.

## Repository structure

| File | Description |

| `WaterAllocationData_Synthetic.xlsx` | Input data — sheets: `WaterSources`, `Demand`, `SocialParams`. |
| `water_model.py` | Model engine (`DataManager` + `WaterAllocationModel` classes); imported by the GUI. |
| `WaterAllocationModel.ipynb` | Self-contained Jupyter notebook — run cell-by-cell for development and exploration. |
| `app.py` | Streamlit GUI wrapping the engine for non-coders. |
| `run_Streamlit_GUI_app.bat` | Windows launcher for the GUI. |

## Installation

Requires Python 3.9+.

```bash
pip install pandas numpy scipy streamlit openpyxl jupyter
```

## Usage

**Notebook (development / exploration):**

```bash
jupyter notebook WaterAllocationModel.ipynb
```

Run the cells top to bottom. The `DATA_FILE` constant in the first cell points to the input workbook — change it to run a different case study.

**Streamlit GUI (interactive):**

```bash
streamlit run app.py
```

On Windows you can instead double-click `run_Streamlit_GUI_app.bat`. The app opens at `http://localhost:8501`, where you can upload data, run the optimization, and explore the Pareto front, per-solution allocations, and regional analysis.

## Input data format

Input is a single Excel workbook with three sheets:

- **WaterSources** — available sources, treatment technologies, and their unit cost, energy, and CO₂ factors; a `feasible` flag drops physically/economically unrealistic pathways before solving.
- **Demand** — system-wide demand per end-use sector.
- **SocialParams** — per-region population, income, employment coefficients, and per-sector demand, used to compute the equity indicators in OF3.

To run your own case study, supply a workbook following the same schema and point `DATA_FILE` at it.

## Synthetic dataset

The bundled `WaterAllocationData_Synthetic.xlsx` is a **synthetic, illustrative** three-region case (Region A: surplus; Region B: deficit; Region C: borderline), with five sources, seven treatment technologies, and 60 feasible pathways. Its numbers are pedagogical — calibrated to realistic *relative* cost and energy ratios to demonstrate model behavior — and are **not** real-world measurements.

## Citation

If you use AquaOptima in your work, please cite:
https://doi.org/10.5281/zenodo.20419731
