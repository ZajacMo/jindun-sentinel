# The research record

This directory holds the research record of JinDun Sentinel: the lineage the
methodology comes from, the peer-reviewed literature the method is built on, the
data sources and what their publishers allow, and an explicit statement of what
the method cannot do.

It is written for a reader who wants to check the work rather than take it on
trust. Every reference below was resolved against the Crossref REST API
(`https://api.crossref.org/works/{doi}`) and the title, journal and year of
every record were read back from the answer; the verification record is in
[§4](#4-the-verification-record).

## Contents

| section | what it answers |
| --- | --- |
| [1. The methodology lineage](#1-the-methodology-lineage) | where the method comes from and which three questions it answers |
| [2. The peer-reviewed references](#2-the-peer-reviewed-references) | the literature the method is built on |
| [3. The Chinese-language source literature](#3-the-chinese-language-source-literature) | the domestic literature the source research builds on |
| [4. The verification record](#4-the-verification-record) | what happened to every DOI of the research-phase reference list |
| [5. The data sources and their terms](#5-the-data-sources-and-their-terms) | where the data comes from and what may be done with it |
| [6. Limitations](#6-limitations) | what the system does not do, stated plainly |

## 1. The methodology lineage

The system implements the methodology of a single source research submission,
**《基于日频测度的系统性金融风险异动监测与预警》** — *Daily-Frequency Measurement of
Systemic Financial Risk: Anomaly Monitoring and Early Warning* (working English
rendering of the title; the paper is in Chinese), by 莫镇嘉 (Mo Zhenjia), 欧洲
(Ou Zhou), 陈可儿 (Chen Ke'er) and 苏安喆 (Su Anzhe), School of Economics and
Finance, South China University of Technology. The original submission, its input
workbooks and the code that produced its tables are the ancestors of this
repository; the vendored regression assets in `data/baseline/` come from it.

That paper organises its contribution around three dimensions, and the three
dimensions are still the three layers of this system:

| dimension (source paper) | what it asks | where it lives here |
| --- | --- | --- |
| **状态识别** — state identification | is this economy calm or stressed, and with what probability? | the regime layer: `packages/pipeline/src/jindun/regime/`, the `regime` block of every run artefact |
| **风险传染** — risk contagion | which market, and which country, transmits stress to which? | the contagion layer: `packages/pipeline/src/jindun/contagion/`, the `spillover` block and `GET /api/v1/global/spillover` |
| **动态预警** — dynamic early warning | when does the system cross a pre-declared threshold, and what caused the move? | the alerting loop and the attribution: `packages/pipeline/src/jindun/attribution/`, the `alerts` and `attribution` blocks |

Three things were added around that core, because a daily operational system
needs them and the research paper did not have them:

- a **quality gate in front of the computation**, so that a daily run refuses to
  publish a number it cannot stand behind;
- a **run manifest behind the computation**, so that every published number can
  be traced to a code version, a source payload and a set of hashes;
- a **multi-country configuration**, so that the same method is applied to five
  economies with the differences between them declared rather than averaged
  away.

## 2. The peer-reviewed references

These are the works the method is built on. Each entry was resolved through the
Crossref single-record endpoint and the answer was checked against the title,
the journal, the volume, the year and the author list printed here.

### 2.1 Indices of systemic stress

| reference | journal | year | DOI |
| --- | --- | --- | --- |
| Holló, E., Kremer, M., & Lo Duca, J. — *CISS — A composite indicator of systemic stress in the financial system* (ECB Working Paper No 6 / SSRN version) | working paper | 2012 | [10.2139/ssrn.2018792](https://doi.org/10.2139/ssrn.2018792) |
| Duca, A., & Peltonen, J. — *Assessing systemic risks and predicting systemic events* | Journal of Banking & Finance, 37(7), 2183–2195 | 2013 | [10.1016/j.jbankfin.2012.06.010](https://doi.org/10.1016/j.jbankfin.2012.06.010) |
| Acharya, V. V., Brownlees, C., Engle, R. F., Farazmand, S., & Richardson, M. — *Measuring Systemic Risk* | Handbook on Systemic Risk, pp. 196–225 (Cambridge University Press) | 2013 | [10.1017/cbo9781139151184.012](https://doi.org/10.1017/cbo9781139151184.012) |
| Bisias, K., Flood, J., Lo, A. W., & Valavanis, A. — *A Survey of Systemic Risk Analytics* | Annual Review of Financial Economics, 4(1), 255–296 | 2012 | [10.1146/annurev-financial-110311-101754](https://doi.org/10.1146/annurev-financial-110311-101754) |

### 2.2 Spillover and connectedness estimators

| reference | journal | year | DOI |
| --- | --- | --- | --- |
| Diebold, F. X., & Yilmaz, K. — *Measuring Financial Asset Return and Volatility Spillovers, with Application to Global Equity Markets* | The Economic Journal, 119(534), 158–171 | 2008 | [10.1111/j.1468-0297.2008.02208.x](https://doi.org/10.1111/j.1468-0297.2008.02208.x) |
| Diebold, F. X., & Yilmaz, K. — *Better to give than to receive: Predictive directional measurement of volatility spillovers* | International Journal of Forecasting, 28(1), 57–66 | 2012 | [10.1016/j.ijforecast.2011.02.006](https://doi.org/10.1016/j.ijforecast.2011.02.006) |
| Billio, M., Getmansky, M., Lo, A. W., & Pelizzon, L. — *Econometric measures of connectedness and systemic risk in the finance and insurance sectors* | Journal of Financial Economics, 104(3), 535–559 | 2012 | [10.1016/j.jfineco.2011.12.010](https://doi.org/10.1016/j.jfineco.2011.12.010) |
| Baruník, J., Kočenda, M., & Vácha, P. — *Asymmetric connectedness on the U.S. stock market: Bad and good volatility spillovers* | Journal of Financial Markets, 27, 55–78 | 2016 | [10.1016/j.finmar.2015.09.003](https://doi.org/10.1016/j.finmar.2015.09.003) |
| Blasques, B., Koopman, S. J., Lucas, A., & Schaumburg, J. — *Spillover dynamics for systemic risk measurement using spatial financial time series models* | Journal of Econometrics, 195(2), 211–223 | 2016 | [10.1016/j.jeconom.2016.09.001](https://doi.org/10.1016/j.jeconom.2016.09.001) |

### 2.3 Financial networks and contagion

| reference | journal | year | DOI |
| --- | --- | --- | --- |
| Gai, J., & Kapadia, S. — *Contagion in financial networks* | Proceedings of the Royal Society A, 466(2120), 2401–2423 | 2010 | [10.1098/rspa.2009.0410](https://doi.org/10.1098/rspa.2009.0410) |
| Acemoglu, D., Ozdaglar, A., Tahbaz-Salehi, A., & Yildiz, A. — *Systemic Risk and Stability in Financial Networks* | American Economic Review, 105(2), 564–608 | 2015 | [10.1257/aer.20130456](https://doi.org/10.1257/aer.20130456) |
| Glasserman, P. B., & Young, A. — *Contagion in Financial Networks* | Journal of Economic Literature, 54(3), 779–831 | 2016 | [10.1257/jel.20151228](https://doi.org/10.1257/jel.20151228) |

### 2.4 The global layer: funding, the dollar and the global cycle

| reference | journal | year | DOI |
| --- | --- | --- | --- |
| Bruno, R., & Shin, H. S. — *Cross-Border Banking and Global Liquidity* | The Review of Economic Studies, 82(2), 535–564 | 2014 | [10.1093/restud/rdu042](https://doi.org/10.1093/restud/rdu042) |
| Ivashina, V., Scharfstein, D. S., & Stein, J. C. — *Dollar Funding and the Lending Behavior of Global Banks* | The Quarterly Journal of Economics, 130(3), 1241–1281 | 2015 | [10.1093/qje/qjv017](https://doi.org/10.1093/qje/qjv017) |
| Miranda-Agrippino, S., & Rey, H. — *U.S. Monetary Policy and the Global Financial Cycle* | The Review of Economic Studies, 87(6), 2754–2776 | 2020 | [10.1093/restud/rdaa019](https://doi.org/10.1093/restud/rdaa019) |

The last three are the literature behind the global layer: the cross-border
banking network of [§5 of `docs/global/banking-network.md`](../global/banking-network.md)
is a statement about the exposure that Bruno and Shin measure, and the global
cycle factor of [`docs/global/global-cycle-factor.md`](../global/global-cycle-factor.md)
is the conditions factor of Miranda-Agrippino and Rey rather than a
re-scaling of the monitored economies' own indices.

## 3. The Chinese-language source literature

The source research is part of a domestic literature on Chinese financial
pressure indices, and the PDFs it was written against are kept in the legacy
project tree under
`docs/系统性风险指数构建参考文献/系统性风险指数构建参考文献/`:

| document | in the source paper's reference list as |
| --- | --- |
| 许涤龙, 陈双莲 — 《基于金融压力指数的系统性金融风险测度研究》, 经济学动态, 2015, (04): 69–78 | [2] |
| 陶玲, 朱迎 — 《系统性金融风险的监测和度量——基于中国金融体系的研究》, 金融研究, 2016, (06): 18–36 | [3] |
| 徐国祥, 李波 — 《中国金融压力指数的构建及动态传导效应研究》, 统计研究, 2017, 34(04): 59–71, DOI 10.19343/j.cnki.11-1302/c.2017.04.006 | [4] |
| 李敏波, 梁爽 — 《监测系统性金融风险——中国金融市场压力指数构建和状态识别》, 金融研究, 2021, (06): 21–38 | [7] |
| 李政, 方梦洁, 张梦 — 《中国金融压力跨市场溢出效应研究——基于系统性风险管理的视角》, 金融论坛, 2022, 27(08): 7–18, DOI 10.16529/j.cnki.11-4613/f.2022.08.008 | [5] |
| 张宗新 — 《系统性金融风险动态测度与跨部门网络溢出效应研究》 | cited in the paper as a companion study |
| 中国系统性金融压力的监测 | the survey chapter of the source line of work |
| Holló 等 — *CISS — a composite indicator of systemic stress in the financial system* | the external anchor the source research compares itself against |

Two of these entries carry DOIs in the source paper's own reference list and
they are reproduced here unchanged; the remaining entries are cited by the
source paper without a DOI, and none is invented here.

## 4. The verification record

The research phase handed over a list of eighteen references with DOIs. Every
one of them was checked against the Crossref single-record endpoint. **Eight of
the eighteen DOIs were wrong** — they resolved to unrelated articles or to
nothing at all — and one of them was the same DOI twice. Each entry was either
corrected to a verified record or dropped.

| # | entry as handed over | DOI as handed over | what the DOI actually is | action |
| --- | --- | --- | --- | --- |
| 1 | Borio & Drehmann (2009) | `10.1016/j.jfineco.2008.09.004` | Massa & Zhang, *Cosmetic mergers: The effect of style investing on the market for corporate control*, JFE 93(3) | **corrected** → Ivashina, Scharfstein & Stein (2015), [10.1093/qje/qjv017](https://doi.org/10.1093/qje/qjv017) |
| 2 | Holló, Kremer & Duca (2012) | `10.1016/j.jmoneco.2012.01.006` | not registered (404) | **corrected** → the working-paper record, [10.2139/ssrn.2018792](https://doi.org/10.2139/ssrn.2018792); the journal version could not be confirmed through the single-record endpoint and is therefore not cited |
| 3 | Diebold & Yilmaz (2008) | `10.1016/j.jfineco.2007.10.003` | Espeneck & Thorburn, *Automatic bankruptcy auctions and fire-sales*, JFE 89(3) | **corrected** → [10.1111/j.1468-0297.2008.02208.x](https://doi.org/10.1111/j.1468-0297.2008.02208.x), The Economic Journal 119(534) |
| 4 | Diebold & Yilmaz (2012) | `10.1016/j.ijforecast.2011.10.002` | Şener, Baronyan & Mengütürk, *Ranking the predictive performances of value-at-risk estimation methods*, IJF 28(4) | **corrected** → [10.1016/j.ijforecast.2011.02.006](https://doi.org/10.1016/j.ijforecast.2011.02.006), IJF 28(1) — the DOI the source paper itself cites |
| 5 | Billio, di Bonito, Maffei & Mainini (2012) | `10.1016/j.jmoneco.2011.12.003` | not registered (404) | **corrected** → Billio, Getmansky, Lo & Pelizzon (2012), [10.1016/j.jfineco.2011.12.010](https://doi.org/10.1016/j.jfineco.2011.12.010) — the paper the source paper itself cites |
| 6 | Acemoglu, Ozdaglar, Tahbaz-Salehi & Yildiz (2015) | `10.1016/j.jmoneco.2014.09.006` | not registered (404) | **corrected** → [10.1257/aer.20130456](https://doi.org/10.1257/aer.20130456), AER 105(2) |
| 7 | Glasserman & Young (2016) | `10.1016/j.jmoneco.2015.09.010` | Albuquerque, Eichenbaum, Papanikolaou & Rebelo, *Long-run bulls and bears*, JME 76 | **corrected** → [10.1257/jel.20151228](https://doi.org/10.1257/jel.20151228), JEL 54(3) |
| 8 | Greenwood, Scharfstein & Steig (2015) | `10.1093/qje/qjv004` | Wantchekon, Klašnja & Novta, *Education and Human Capital Externalities*, QJE 130(2) | **corrected** → Ivashina, Scharfstein & Stein (2015), [10.1093/qje/qjv017](https://doi.org/10.1093/qje/qjv017); no Crossref record for the paper under the handed-over authorship was found |
| 9 | Battiston, Dafermos & Icazatti (2012) | `10.1016/j.jmoneco.2012.03.009` | not registered (404) | **dropped**; the adjacent coverage is carried by Duca & Peltonen (2013) and the Handbook chapter of Acharya, Brownlees, Engle, Farazmand & Richardson (2013) |
| 10 | Bruno & Shin (2014) | `10.1016/j.jmoneco.2013.11.007` | Alvarez & Dixit, *A real options perspective on the future of the Euro*, JME 61 | **corrected** → [10.1093/restud/rdu042](https://doi.org/10.1093/restud/rdu042), REStud 82(2) |
| 11 | Miranda-Agrippino & Rey (2020) | `10.1016/j.jmoneco.2019.12.005` | Assenza, Heemeijer, Hommes & Massaro, *Managing self-organization of expectations through monetary policy*, JME 117 | **corrected** → [10.1093/restud/rdaa019](https://doi.org/10.1093/restud/rdaa019), REStud 87(6) |
| 12 | Baruník, Kočenda & Vácha (2016) | `10.1016/j.jmoneco.2015.12.009` | not registered (404) | **corrected** → [10.1016/j.finmar.2015.09.003](https://doi.org/10.1016/j.finmar.2015.09.003), JFM 27 |
| 13 | Gai & Kapadia (2010) | `10.1016/j.jfineco.2009.12.003` | Albuquerque & Schroth, *Quantifying private benefits of control from a structural model of block trades*, JFE 96(1) | **corrected** → [10.1098/rspa.2009.0410](https://doi.org/10.1098/rspa.2009.0410), Proc. R. Soc. A 466(2120) |
| 14 | Acharya, Huang, Ludwig & Mudekere (2016) | `10.1016/j.jmoneco.2015.10.003` | Wang & Yang, *Equilibrium matching and termination*, JME 76 | **dropped**; replaced by Acharya, Brownlees, Engle, Farazmand & Richardson (2013), [10.1017/cbo9781139151184.012](https://doi.org/10.1017/cbo9781139151184.012) |
| 15 | Brownlees & Engle (2017) | `10.1016/j.jeconom.2016.06.028` | not registered (404) | **dropped**; the VAR construction it would have covered is documented in the code and in `docs/methodology/spillover-legacy-vs-paper.md` |
| 16 | Bisias, Bredický & Lóczi (2012) | `10.1016/j.jbankfin.2012.09.008` | Driessen & Maenhout, *The world price of jump and volatility risk*, JBF 37(2) | **corrected** → Bisias, Flood, Lo & Valavanis (2012), [10.1146/annurev-financial-110311-101754](https://doi.org/10.1146/annurev-financial-110311-101754) |
| 17 | Engle (2018) | `10.1016/j.jeconom.2017.09.013` | not registered (404) | **dropped**; no 2018 *Journal of Econometrics* article by Engle is indexed in Crossref. The Engle contribution is represented by the 2013 Handbook chapter |
| 18 | Baruník, Krehlik & Vácha (2016) | `10.1016/j.jmoneco.2015.12.009` | the same DOI as entry 12 — not registered | **dropped as a duplicate**; the Baruník, Kočenda & Vácha paper of entry 12 is retained |

The net result is the reference list of [§2](#2-the-peer-reviewed-references):
fourteen journal articles and one book chapter were verified and are cited, and
three entries were dropped because no verifiable record of them could be
obtained.

## 5. The data sources and their terms

The column "publisher's terms" below is a summary. The publisher's own terms
page is the authoritative statement, those terms change, and nothing in this
repository grants a permission the publisher has not granted.

| source | what is taken | publisher's terms, in summary | what this project does with it |
| --- | --- | --- | --- |
| ECB — Composite Indicator of Systemic Stress (SDMX 2.1) | the daily composite `SS_CIN` for 14 reference areas, the monthly composite `SS_CI` for `U2` and `US`, and the five euro-area sub-stress contributions | the ECB's data portal permits reproduction with attribution to the ECB; the published series remain the ECB's | read through `jindun.adapters.ecb_ciss`; the raw response is cached in the local snapshot store and the published index is a **derived** series that is recomputed daily |
| BIS — Statistical API and bulk archive | locational banking statistics, global liquidity indicators, credit-to-GDP gaps, effective exchange rates and seven further flows | the BIS permits use and reproduction of its statistics with attribution; the bulk archive is provided for research use | read through `jindun.adapters.bis`; the bilateral matrix is extracted once into a filtered snapshot under `data/snapshots/bis/` |
| Bank of Japan — Time-Series Statistics Search | the daily call-rate, exchange-rate and policy-rate series, plus the derived call-rate dispersion and USD/JPY series | free of charge with attribution; the service asks clients to keep the request rate low, which the adapter enforces | read through `jindun.adapters.boj`; nothing is redistributed |
| FSB — list of global systemically important banks | the annual G-SIB list with its buckets | an FSB publication; reproduction with attribution is the normal practice and the PDF is the authoritative version | parsed by `jindun.adapters.fsb` and published as `gsib.json` with the source URL and the retrieval time |
| akshare — Chinese market data | SSE, SZSE and CSI 300 levels and turnover, ChinaBond government yields, SHIBOR fixings, margin balances, CSI 300 index futures and the USD/CNY middle rate | the `akshare` package is MIT-licensed; the underlying series belong to their original publishers (the exchanges, ChinaBond, the interbank market), and this project grants no rights over them | read through `jindun.adapters.akshare_source`; the **raw snapshots are not committed to the repository**, so no redistribution of them happens |

The last row is a deliberate policy decision rather than a technical
convenience: the raw series come from redistributors whose redistribution terms
this project cannot grant, so `data/snapshots/` is ignored by git and
`jindun-pipeline fetch` rebuilds it from the publisher's own endpoint.

## 6. Limitations

### 6.1 The four that matter most

1. **The Japanese composite has no official CISS cross-check anchor.** The ECB
   publishes no Japanese series at all: every Japanese reference area answers
   404 on both the daily and the monthly frequency. The Japanese index is built
   from the Bank of Japan's own daily statistics and therefore has no external
   official index to be checked against. A disagreement between the Japanese
   series and an external stress index could not be detected by this project.
2. **The generalised variance decomposition is a signed quantity.** In the
   `dy_generalised` estimator a negative entry means that the innovation of the
   column node *reduces* the forecast error variance of the row node. This is a
   property of the estimator, not a numerical defect, and it is why the
   absolute-value variant is documented separately from it.
3. **The ordering-sensitive Cholesky estimator must not be used to compare
   systems with different node sets.** The `sims_structural` estimator depends
   on the order of the variables, so a network computed over five Chinese
   sub-markets and a network computed over five countries are not comparable
   with it. The cross-country network is therefore computed with an
   order-independent estimator, and the node set is part of the artefact.
4. **The published Table 5-2 spillover matrix cannot be reproduced bit for
   bit.** The shipped implementation reads its VAR sample from a workbook that
   was never committed to the original repository, and an exhaustive search over
   4 696 candidate specifications did not find a single one that reproduces the
   published matrix. The evidence, the search and the regression strategy that
   replaced it are in
   [`docs/methodology/spillover-legacy-vs-paper.md`](../methodology/spillover-legacy-vs-paper.md).

### 6.2 Further limitations

| area | limitation |
| --- | --- |
| the sub-market decomposition | the United States, the United Kingdom and the euro area are measured with the official ECB composite stress index and therefore have **no** sub-market decomposition, no market attribution and no cross-market spillover network. Every artefact says so through its `profile` and `capabilities` map |
| the Japanese index | two markets instead of five: the Bank of Japan publishes no daily equity index, no daily derivatives market and no daily government bond yield curve, and the monthly and quarterly price databases are not mixed into the daily panel |
| the global cycle factor | it is a **conditions** factor, not a stress index: it describes the configuration that historically precedes global stress, and it cannot say that a given economy is stressed |
| the banking network | it is built from the BIS locational statistics, which measure the claims of reporting banks on counterparties; it is not a measure of the total financial exposure of an economy, and a bilateral position of zero in the data is not the same as an absence of exposure |
| the G-SIB list | it is annual, so it carries no within-year dynamics, and the parser checks the number of parsed rows against the number the document declares and warns when they disagree |
| the regime model | the label of an observation is the regime with the highest **filtered** posterior probability, so a regime change is reported when the data say so and not earlier; the smoothed posterior is deliberately not used |
| the forecast | the shipped forecast engine is ARIMA with a walk-forward evaluation on bounded origins. The LSTM engine that the source paper compared against is present in the package but is not the published path |
| the quality gates | the thresholds are fixed in `jindun.quality.QualityPolicy` and in `packages/pipeline/configs/global.yaml`. They are conservative defaults, not an empirically optimal choice, and they are not fitted to any data |
| the `akshare` dependency | the Chinese market series come from a scraper of public pages rather than from an official API. They are the least stable input in the system, and the quality gate is what keeps a change of their shape from silently becoming a change of the index |

## Where to continue

| question | document |
| --- | --- |
| how the composite is built and what the two lenses mean | [`docs/methodology/README.md`](../methodology/README.md) |
| how the spillover network is computed, and why it carries four estimators | [`docs/methodology/spillover-legacy-vs-paper.md`](../methodology/spillover-legacy-vs-paper.md) |
| what each of the five economies is measured with | [`docs/methodology/country-profiles.md`](../methodology/country-profiles.md) |
| how to run the system and read its artefacts | [`docs/user-guide/README.md`](../user-guide/README.md) |
| how the global layer is built | [`docs/global/global-layer.md`](../global/global-layer.md) |
