# Methodology

The methodology documentation of JinDun Sentinel. It states what is computed,
under which assumptions, with which caveats, and where the code that computes it
lives.

Two rules hold throughout:

- **Every statement about the method is checkable against the code.** Each
  section names the module that implements it, so a reader who disagrees with a
  claim can go and read the lines that produce the number.
- **Nothing is silently aligned.** Where the implementation deviates from the
  published specification of the source research, the deviation is documented
  and quantified rather than quietly fixed.

## The documents

### Written

| document | what it covers |
| --- | --- |
| [`spillover-legacy-vs-paper.md`](spillover-legacy-vs-paper.md) | **The contagion methodology.** The published specification of the variance decomposition (equations (6) and (7) of the source research), the implementation that actually shipped with the previous system, the four estimators the current pipeline computes, and a quantified account of why the originally published Table 5-2 cannot be reproduced bit for bit. Read this before comparing any two spillover numbers in this project. |
| [`country-profiles.md`](country-profiles.md) | **What each economy is measured with.** The two profiles (`mbsed` and `official_index`), what the five economies have and do not have, why the tertiary indicators are not built for the three economies measured by an official index, and what every run artefact records about it. |
| [`../global/global-layer.md`](../global/global-layer.md) | **The global layer.** Cross-country contagion, the global financial cycle factor, the cross-border banking network and the G-SIB list, and what the global layer deliberately does not do. |
| [`../global/global-cycle-factor.md`](../global/global-cycle-factor.md) | **The global financial cycle factor.** The question the factor answers, its nine published BIS inputs, the construction, the sign orientation, the country-panel cross-check, and the three properties of the published BIS data that change how the files have to be read. |
| [`../global/banking-network.md`](../global/banking-network.md) | **The cross-border banking network.** What is measured, the filter applied to the BIS locational statistics, why the bulk archive and not the API, the treatment of the euro area, and the limitations of a bilateral claims matrix. |

### Planned

The following documents are not written yet. Their scope is fixed here so that
the plan is a contract rather than a wish.

| document | what it will cover |
| --- | --- |
| `composite-index.md` | **The construction of the composite index.** The cumulative-distribution normalisation and the three indicator directions (same, opposite, bidirectional), the sub-market principal component analysis and the 80 % cumulative explained-variance rule, the CRITIC objective weighting and how it interacts with the configured weights, the weighted-correlation form of the MBSED composite `sqrt((W ⊙ s) P (W ⊙ s)' × 2)`, and the arithmetic that relates a market's weight to the composite. |
| `regime.md` | **The regime identification and the risk probability model.** The Markov-switching autoregression on the log composite, why the **filtered** posterior probability is used and the smoothed one is not, the labelling rule that puts the calm regime first, the two-component normal mixture whose locations and dispersions are estimated from the fit rather than hard-coded, and the deterministic fallback used when the maximum-likelihood fit does not converge. |
| `comparability.md` | **The comparability note on the two lenses.** Why the within-country percentile is the lens that can be compared across jurisdictions and what the deviation-from-own-trend lens is for, what each lens can and cannot support, and why the cross-country network is built on the percentile lens only. |

## How the pieces fit together

The chain is linear, and each step has exactly one owner document:

```
sources ──▶ adapters ──▶ quality gates ──▶ normalisation ──▶ sub-market PCA
                                                                    │
                                       MBSED composite ◀─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    ▼                         ▼                         ▼
             regime + probability      spillover network            attribution
                    │                         │
                    └────────▶ alerting rules ◀────────┘
                                      │
                                      ▼
                        artefacts + run manifest
                                      │
                                      ▼
                            API ──▶ web front end
```

| step | implemented in | documented in |
| --- | --- | --- |
| fetch and cache the raw payloads | `jindun.adapters.*`, `jindun.adapters.base.SnapshotStore` | the coverage table of the root [README](../../README.md#data-coverage) |
| reject what cannot be used | `jindun.quality` | the root [README](../../README.md#data-coverage) and the `quality.json` artefact |
| normalise the tertiary indicators | `jindun.index.normalise` | `composite-index.md` *(planned)* |
| reduce each market to a factor and build its stress index | `jindun.index.pca`, `jindun.index.critic` | `composite-index.md` *(planned)* |
| synthesise the MBSED composite and its two lenses | `jindun.index.composite` | `composite-index.md` *(planned)* |
| identify the regime and the risk probability | `jindun.regime.markov`, `jindun.regime.probability` | `regime.md` *(planned)* |
| estimate the spillover network | `jindun.contagion.var`, `jindun.contagion.gvd` | [`spillover-legacy-vs-paper.md`](spillover-legacy-vs-paper.md) |
| detect a spill-out surge | `jindun.contagion.surge` | [`spillover-legacy-vs-paper.md`](spillover-legacy-vs-paper.md) |
| attribute the last move | `jindun.attribution` | `composite-index.md` *(planned)* |
| evaluate the alerting rules | `jindun.pipeline._evaluate_alerts`, `packages/pipeline/configs/global.yaml` | the root [README](../../README.md#the-four-layers) |
| build the cross-country layer | `jindun.global_layer` | [`../global/global-layer.md`](../global/global-layer.md) |
| state what may be compared with what | — | `comparability.md` *(planned)* |

## The order in which a researcher should read them

1. **[`country-profiles.md`](country-profiles.md)** — first, because it decides
   what the numbers are. Not every economy in the table is measured the same
   way, and the differences change what a comparison between two of them
   means.
2. **[`spillover-legacy-vs-paper.md`](spillover-legacy-vs-paper.md)** — second,
   because the contagion network is the part of the system with the most
   freedom of interpretation: four estimators that are not interchangeable, one
   reporting convention, and a published matrix that cannot be reproduced.
3. **`composite-index.md` *(planned)*** — third, for the construction of the
   index itself: the normalisation, the factor reduction, the weights and the
   composite.
4. **`regime.md` *(planned)*** — fourth, for the state model that turns the
   index into a probability.
5. **`comparability.md` *(planned)*** — fifth, and then always: it is the note
   that decides which statements the numbers support.
6. **[`../global/global-layer.md`](../global/global-layer.md)** and its two
   companions — last, if the interest is in the cross-country layer rather than
   in the country layer.

## Conventions used in these documents

| convention | meaning |
| --- | --- |
| `module.function` | a Python path inside the repository; the reader can open it and read the code |
| `artefact` | a file the pipeline writes under `data/runs/`; its shape is fixed by the code that writes it |
| *lens* | the view a number is reported through: the within-country percentile or the deviation from the country's own trend |
| *profile* | what a country's index is: `mbsed` (synthesised) or `official_index` (a published official index) |
| *estimator* | one of the four spillover estimators, named `paper_equation`, `sims_structural`, `dy_generalised` or `legacy_appendix` |

## Where the numbers come from

The research record — the lineage of the method, the peer-reviewed literature
it is built on, the data sources and their terms, and the limitations of the
result — is in [`../research/README.md`](../research/README.md). The
limitations there bind the documents here: where this directory states what a
number means, the research record states what it does not mean.
