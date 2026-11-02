# Spillover estimators: published specification vs. shipped code vs. current implementation

This note records exactly how the cross-market (and cross-country) spillover
network is computed, why the project carries more than one estimator, and why
the matrix published as Table 5-2 of the original paper **cannot** be
reproduced bit for bit from the data that survives in the repositories.

Nothing here is silently aligned. Every estimator is implemented, tested and
named, and the differences are quantified below.

---

## 1. The published specification

The competition-submission paper defines the decomposition in section 5.2.1.
The formulas were transcribed from the document's OMML (the equations are
embedded as Word math objects, not as text), so they are reproduced here
verbatim rather than paraphrased.

Equation (4) — the VAR:

```
y_t = A_1 y_{t-1} + ... + A_p y_{t-p} + u_t
```

Equation (5) — the VMA(∞) representation:

```
y_t = sum_{k=0}^{inf} Psi_k u_{t-k},   Psi_0 = I
```

Equation (6) — the generalised variance decomposition:

```
                sum_{k=0}^{H-1} ( e_i' A_k e_j )^2 * eps_jj
Y_ij^H  =  ---------------------------------------------
                sum_{k=0}^{H-1} ( e_i' A_k A_k' e_i )
```

Equation (7) — the normalised (share) matrix:

```
                        Y_ij^H
Ytilde_ij^H  =  ---------------------------
                 sum_{j=1}^{n} Y_ij^H
```

where `eps_jj` is the variance of the estimation error of the `j`-th equation
and `e_j` is the unit vector with a one in position `j`.

Two consequences follow immediately and both are implemented in
`jindun.contagion.gvd`:

1. **The reporting convention is row-normalised.** `Ytilde[i][j]` is the share
   of node `i`'s own forecast error variance that is attributable to node `j`.
   Consequently the *column* off-diagonal sum is how much of the system a node
   causes (total spill-out) and the *row* off-diagonal sum is how much of a
   node's own variance comes from elsewhere (total spill-in).
2. **The denominator of equation (6) cancels** in equation (7): it does not
   depend on `j`, so only the shape of the numerator survives the
   normalisation. The implementation still evaluates it so the code can be
   checked against the paper line by line.

## 2. The code that actually shipped

The "core algorithm code" appendix of the same submission contains the
implementation that produced the published tables. It is transcribed here
because it differs from the equations above in two ways that matter.

```python
lag_order = 5
results = VAR(data_var).fit(lag_order)
a_matrices = results.coefs
sigma = results.sigma_u
H = 5
for j in range(len(markets)):
    for k in range(len(markets)):
        denominator = abs(sigma.iloc[k,k]) * sum(
            sigma @ a_matrices[:H,j] @ a_matrices[:H,j].T
        )
        theta_jk = sum((sigma @ a_matrices[:H, k]) ** 2) * abs(sigma.iloc[j,k]) / denominator
        temp[j,k] = abs(theta_jk)
for j in range(len(markets)):
    for k in range(len(markets)):
        spillover_index[j, k] = temp[j,k] / sum(temp[j])
```

Two structural quirks are baked into this code:

* **The matrix product is only defined when `H` equals the number of nodes.**
  `sigma` is `k x k` and `a_matrices[:H, j]` is `H x k`, so
  `sigma @ a_matrices[:H, j]` requires `k == H`. The published run used five
  markets and `H = 5`, so the two happened to agree; the code raises a
  `ValueError` for any other combination. The current implementation
  reproduces this constraint explicitly
  (`jindun.contagion.gvd.legacy_appendix_spillover`).
* **The index convention differs between the numerator and the denominator.**
  The denominator is built from the *row* of the coefficient stack selected by
  the outer loop index `j`, while the numerator uses the *column* selected by
  the inner index `k`. The result is not a forecast error variance
  decomposition; algebraically it is a **residual-correlation weighted index**
  scaled by the response magnitudes.

The current pipeline keeps this implementation available as the
`legacy_appendix` method so that published numbers can be regenerated, and it
is explicitly labelled as such in the returned notes.

## 3. The estimators in the current pipeline

| method | what it is | order-dependent | signed | default |
| --- | --- | --- | --- | --- |
| `paper_equation` | equations (6) and (7) of the paper | no | no | **yes** |
| `sims_structural` | Sims (1980) FEVD, Cholesky, unit-variance structural shocks | yes | no | no |
| `dy_generalised` | Diebold-Yilmaz (2009, 2012) generalised FEVD | no | yes | no |
| `legacy_appendix` | literal transcription of the shipped code | no | no | no |

Notes on the individual methods:

* **`paper_equation`** implements the published specification literally. The
  reduced-form VMA coefficients `Psi_k` are used for `A_k`, and `eps_jj` is the
  variance of the `j`-th equation's estimation error. The result is
  non-negative and every row sums to one.
* **`sims_structural`** is the estimator most practitioners mean by
  "spillover". It is non-negative but inherits the Cholesky ordering
  artefact, so it must not be used to compare systems whose node sets or node
  orders differ.
* **`dy_generalised`** does not require contemporaneous independence and is
  therefore free of the ordering artefact. It is a **signed** quantity: a
  negative entry means the innovation of the column node *reduces* the
  forecast error variance of the row node. That is a property of the
  estimator, not a numerical defect.
* **`legacy_appendix`** exists for regression against the previous system only.

All four share the same reporting convention (row-normalised shares, total
spill-out as the column off-diagonal sum, total spill-in as the row
off-diagonal sum), so they are directly comparable in presentation even when
they are not comparable in substance.

## 4. Why Table 5-2 cannot be reproduced bit for bit

The published matrices are:

| | equity | bond | fx | money | derivative |
| --- | --- | --- | --- | --- | --- |
| **equity** | 0.971463 | 0.009948 | 0.001805 | 0.000433 | 0.016351 |
| **bond** | 0.080189 | 0.880632 | 0.010749 | 0.024040 | 0.004391 |
| **fx** | 0.049396 | 0.036482 | 0.875167 | 0.037995 | 0.000961 |
| **money** | 0.005730 | 0.039462 | 0.018376 | 0.913027 | 0.023405 |
| **derivative** | 0.395704 | 0.013183 | 0.000850 | 0.042807 | 0.547456 |

Every row sums to one and every column off-diagonal sum reproduces the
"total spill-out" row of the published table exactly, which confirms that the
reading of the matrix in section 1 is correct.

The obstacle is the input. The shipped code reads its VAR sample from a
workbook named `Database2.xlsx`, which was **never committed to the original
repository**. Two vintages of the market-index series survive:

| vintage | rows | first date | last date |
| --- | --- | --- | --- |
| `output/指数汇总_系统性金融风险维度.xlsx` | 3133 | 2011-11-07 | 2024-10-18 |
| `docs/新文科/...-各指数汇总.xlsx` | 3132 | 2011-11-07 | 2024-10-18 |

They are *not* the same numbers: the equity column differs on every row
(e.g. 0.748679 versus 0.667814 on 2024-10-18), which is the signature of a
re-run of the upstream PCA stage on revised tertiary-indicator data.

A systematic search over the two vintages x {ascending, descending} x
{level, first difference} x VAR orders 1-8 x horizons 1-12 x six formula
variants (4696 candidate specifications in total) produced a best maximum
absolute deviation from Table 5-2 of **0.1116**, and no candidate below
1e-4. The conclusion is that the published matrix depends on a data vintage
that is not recoverable from the repositories.

What *is* reproducible is everything else:

* the algebraic form of the decomposition (equations 6 and 7),
* the shipped implementation, character for character, and
* the reporting convention and the arithmetic identities that link the
  matrix to the total spill-out / spill-in columns.

## 5. Regression assets

The following are vendored under `data/baseline/`:

| file | content |
| --- | --- |
| `cn_legacy_market_indices.csv` | the legacy market and composite index series (3133 rows) |
| `paper_spillover_tables.json` | the published matrices (full sample, pre- and post-2015-crash) |
| `provenance.json` | source path, SHA-256 of the source workbook and of the generated files |

`scripts/freeze_baseline.py` regenerates all three from the legacy tree.

The test suite pins the *estimator* rather than the *published numbers*:

* `tests/test_gvd.py::test_legacy_appendix_matches_an_independent_transcription`
  compares the `legacy_appendix` method against a second, independently
  written transcription of the shipped code and requires exact agreement.
* `tests/test_gvd.py::test_paper_equation_matches_its_own_definition`
  re-derives equations (6) and (7) from the VMA coefficients and compares
  against the implementation.
* `tests/test_gvd.py::test_rows_sum_to_one` and
  `::test_shares_are_non_negative` pin the reporting invariants for every
  non-signed method.

## 6. Which estimator is used where

* **Country market contagion** (five sub-markets of one economy): the default
  `paper_equation` estimator, so the published specification is preserved and
  the numbers remain comparable with the paper.
* **Cross-country contagion** (the global layer): the default
  `paper_equation` estimator as well, with the country composites as nodes.
  The node set changes between runs, so the ordering-sensitive
  `sims_structural` estimator is *not* used there.
* **Legacy regression and figure reproduction**: `legacy_appendix`.

Whenever a correction changes a published number, both the legacy and the
corrected value are kept, the difference is quantified, and the change is
recorded in the release notes — never silently aligned.
