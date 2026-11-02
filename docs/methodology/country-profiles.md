# Country profiles: what each economy is measured with

The five economies of this release are **not** measured with the same
instrument, and pretending otherwise would be the easiest way to publish a
number nobody can reproduce.  This page states exactly what each economy has,
what it does not have, and why.

## The two profiles

| Profile | What the country index is | Economies |
| --- | --- | --- |
| `mbsed` | the MBSED composite, synthesised from the sub-market indices | China, Japan |
| `official_index` | a published official stress index | United States, United Kingdom, Euro Area |

### `mbsed`

The construction of the original research: every market (equity, bond,
foreign exchange, money, derivatives) is built from its tertiary indicators,
the markets are aggregated into one composite with the MBSED weighting, and
the composite carries two reporting lenses (the within-country percentile and
the deviation from the country's own trend).

### `official_index`

The country index *is* a published official stress index.  There is no
sub-market decomposition behind it, and the system says so rather than
publishing an attribution that was never computed: the market attribution and
the cross-market spillover network are not available for these economies.

The consequence for the global layer is nil.  The cross-country network and
the global cycle factor work on the country composites, and the *percentile*
lens is what makes them comparable across economies with different indicator
mixes.

## The five economies

| Economy | Source | Markets | Decomposition | Cross-check anchor |
| --- | --- | --- | --- | --- |
| China | akshare (SSE/SZSE, ChinaBond, SHIBOR, margin balances, index futures, USD/CNY) | 5 | yes | ECB CISS `CN` |
| Japan | BOJ (call rates, USD/JPY) | 2 | yes | **none** |
| United States | ECB CISS `SS_CIN` (area `US`) | 1 | no | the index itself |
| United Kingdom | ECB CISS `SS_CIN` (area `GB`) | 1 | no | the index itself |
| Euro Area | ECB CISS `SS_CIN` (area `U2`) | 1 | no | the index itself |

### China

The only economy with the complete indicator set of the original research, and
the only one where the tertiary indicators survive a live check against a free
service.  The indicators whose original source was a commercial terminal are
kept in `configs/countries/cn.yaml` with `enabled: false` rather than being
quietly replaced by a proxy.

The market weights and the indicator weights reproduce the specification of
the original research: equity 0.30, bond 0.30, foreign exchange 0.10, money
0.20, derivatives 0.10.

### Japan

Japan is the one economy the ECB does not cover: **every** Japanese reference
area of the CISS answers 404, so there is no official cross-check anchor for
the Japanese index, and the methodology pages say so rather than hiding it.

The index is built from the Bank of Japan's own daily statistics:

* **money** — the term structure of the call rate.  The spread between the
  three month and the overnight rate is the classic sign that the money
  market is under strain.
* **foreign exchange** — the USD/JPY spot rate of the Tokyo market, entering
  as realised volatility and as a deviation from trend.  A sharp move in
  either direction is a risk event, which is why the exchange rate enters as a
  volatility rather than as a level.

What the Bank of Japan does **not** publish on a daily frequency is an equity
index, a derivatives market and a government bond yield curve.  Its price
databases (producer prices, the Tankan) are monthly and quarterly, and mixing
them into a daily panel would silently reduce the whole index to the
frequency of its slowest component — so they are not used.  The Japanese
index therefore has two markets instead of five, and the Japanese cross-market
spillover network has two nodes.  That is stated in every run artefact.

### United States, United Kingdom, Euro Area

The ECB publishes the composite indicator of systemic stress daily for the
United States, the United Kingdom and the euro area, and the composite is
built from the same five sub-stresses the MBSED construction uses.  For the
euro area the ECB also publishes the five sub-stresses themselves, so the
euro area is the one economy of this release whose stress can be read in its
components.

## Why not build the tertiary indicators for the other economies?

Because it would mean publishing numbers whose sources have not been read.
Every source in this project was fetched live and its output shape verified
before it was written into a configuration; that work is done for China (the
akshare series) and for Japan (the BOJ series), and it is not done for the
United States, the United Kingdom and the euro area.  The honest position is
to use the official composite for those economies and to say so.

The official index is also *better* in one respect: it is published, revised
and documented by its originator, so its level can be checked against the
ECB's own publication.

## What every run artefact records

* the profile and the markets that were actually available,
* the quality gate outcome for every series,
* the explicit warning when the economy has no sub-market decomposition.

Nothing in the artefacts implies a depth of analysis that was not carried out.
