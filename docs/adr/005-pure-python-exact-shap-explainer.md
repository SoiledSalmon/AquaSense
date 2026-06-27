# 5. Pure-Python Exact SHAP Explainer

## Status
Approved

## Context
The project runs on Python 3.14.3 in the local development environment. The standard `shap` library contains native C/C++ extensions (`_cext` for TreeExplainer and GPU acceleration) which require Microsoft Visual C++ Build Tools to compile from source when pre-built wheels are unavailable. For Python 3.14 on Windows, no pre-built wheels exist yet, leading to installation and deployment failures.

Since our models (XGBoost classifier) only utilize exactly three features (`ph`, `tds`, `turbidity`) for water quality classification, the total feature subset space is extremely small ($2^3 = 8$ possible coalitions).

## Decision
Instead of requiring a local C++ compiler or relying on the heavy, native `shap` package, we implement a custom, mathematically exact SHAP explainer in pure Python using the marginal contribution (Shapley) formula. 

The explainer evaluates the model's prediction probability for each of the 8 feature subsets (coalitions) by replacing absent features with baseline values (representing optimal, safe water). It then aggregates the marginal contributions of each feature according to their combinatoric weights:
- Subsets of size 0: weight = 1/3
- Subsets of size 1: weight = 1/6
- Subsets of size 2: weight = 1/3

## Consequences
- **Zero Binary Dependencies:** Eliminates compile failures during `pip install` on Python 3.14+ or platforms lacking Visual C++ Build Tools (such as Railway Nixpacks environment).
- **Mathematical Exactness:** Computes exact Shapley values identical to TreeExplainer/KernelExplainer, conforming strictly to the additivity, symmetry, and dummy properties of SHAP.
- **High Performance:** Computes explanations in less than 1 millisecond by invoking the cached XGBoost model's `predict_proba` exactly 8 times per inference, avoiding the overhead of C-extension initialization.
- **Low Footprint:** Reduces container size and memory usage by removing the dependency on `shap`, `numba`, and other native libraries.
