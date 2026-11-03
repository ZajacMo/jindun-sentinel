# The global financial cycle factor

`cycle.json` holds the global financial cycle factor — layer L3 of the global
layer — and the country-panel factor it is checked against.

This page states what the factor is, how it is built, and the three
properties of the published BIS data that change how the build has to be
done.  Every number quoted here was produced by the pipeline against the
live BIS service.

## The question the factor answers

The country layer answers "how stressed is this economy".  The global layer
answers what follows from that: "**which economies move together**" and
"**who is exposed to whom**".

A third question sits between them: "**what global condition is the whole
system sitting in**".  That is the global financial cycle of Bruno & Shin
(2014) and Miranda-Agrippino & Rey (2020) — a common driver of credit and
currency conditions that amplifies stress across economies at once and is
visible in the stress indices before it is visible in any one of them.

That object is *not* the same as the average of the monitored indices.  The
average of the stress indices is layer L1; the global cycle is layer L3.  An
earlier release of this project published the layer L1 object under the name
"global cycle factor", which was a category error: a factor built from the
monitored economies cannot show what happens *before* those economies are
stressed.  The layer L1 object is still computed — it is the natural check on
the layer L3 one — but it is reported as the cross-check.

## The inputs

Nine series from three BIS flows.  Every selection is written against the
publisher's own dimension codes, and the title the publisher gives the
selected series is carried into the artefact, so a reader can check the
selection without reading any code.

| Input | Flow | Selection | Unit |
| --- | --- | --- | --- |
| `global_credit_yoy` | `WS_GLI` | all currencies, all countries, non-banks, cross-border, all instruments, year-on-year change | per cent |
| `usd_credit_yoy` | `WS_GLI` | US dollars, countries excluding US residents, non-banks, all lenders, credit, year-on-year change | per cent |
| `eur_credit_yoy` | `WS_GLI` | euros, countries excluding euro-area residents, non-banks, all lenders, credit, year-on-year change | per cent |
| `credit_gap_us` | `WS_CREDIT_GAP` | United States, private non-financial sector, gap (actual minus trend) | percentage points of GDP |
| `credit_gap_cn` | `WS_CREDIT_GAP` | China | percentage points of GDP |
| `credit_gap_jp` | `WS_CREDIT_GAP` | Japan | percentage points of GDP |
| `credit_gap_gb` | `WS_CREDIT_GAP` | United Kingdom | percentage points of GDP |
| `credit_gap_xm` | `WS_CREDIT_GAP` | euro area | percentage points of GDP |
| `eer_us_yoy` | `WS_EER` | nominal, broad basket (64 economies), United States | index, 2020 = 100 |

The euro area's code in the BIS data is `XM`, not the `5C` used by the
locational banking statistics; the country registry maps `EU` to whichever
the flow in question uses.

## The construction

1. Every series is aligned to the **end of its quarter**.
2. The block is **restricted to the quarters every input covers**.  The euro
   area's credit gap starts in 2009, so the factor starts in 2009 even
   though the credit series themselves reach back to the 1950s.
3. Each input is **standardised** against its own history, so a credit gap
   in percentage points and a credit growth rate in per cent can enter the
   same factor.
4. The factor is the **first principal component** of the standardised block.
5. The sign is oriented on the mean of the standardised credit gaps.

## What a higher factor means

The factor is a **conditions** factor, not a stress index.

The sign is oriented so that a higher factor means a **wider credit-to-GDP
gap** together with **slower global credit growth** — the credit cycle
approaching its peak.  That is the configuration that historically precedes
financial stress.

It does **not** mean that stress is already present.  A reader who treats a
rising factor as a rising stress index will read it backwards.

The orientation is not asserted; it is measured.  The mean of the
standardised credit gaps correlates **0.84** with the first component, and
the artefact prints that correlation.  The wording itself is derived from
the estimated loadings, so it cannot drift away from what the factor
actually is.

## What the loadings say

On the current window the first component explains **34.9 %** of the variance
of the input block; the first two together explain 63.3 %.  That is the
honest answer: **these flows do not move as one driver**, and the factor
must not be read as one.

The loadings split the block in a way that is itself informative:

* The credit gaps of the United States (+0.53), the United Kingdom (+0.49),
  Japan (+0.33) and the euro area (+0.29) carry the component.
* Global and dollar credit growth load against them (−0.29 and −0.33):
  credit is above trend precisely when credit growth is decelerating.
* China's credit gap loads against them too (−0.22): the Chinese credit
  cycle is not the same cycle, and the artefact says so rather than
  averaging it away.
* The US dollar's effective exchange rate is **essentially orthogonal** to
  the first component (−0.03).  It forms its own component further down.
  The artefact names the inputs that carry the factor only weakly, so
  "the dollar is in this factor" is not an impression a reader gets.

## The cross-check

The country-panel factor — the first principal component of the aligned
country composites — is computed on the same run.  The quarterly factor is
carried forward onto the daily calendar of the panel and the two are
correlated over the overlap.  On the current window the correlation is
**0.26** over 2 196 daily observations.

Two different objects, a modest positive correlation: the global credit
cycle and the common movement of the monitored stress indices are related
but not the same thing, which is the expected result and the reason both
are published.

## Three properties of the published data that change the build

These were verified against the live BIS service and each one breaks a
naive implementation.

**The bulk files are the only practical route.**  The SDMX API serves the
aggregates of these flows but not the dimension combinations the factor
needs, and a request for a narrow key answers 404.  The bulk flat files are
small — 0.2 MB, 0.2 MB and 6.3 MB — and they are downloaded into the
git-ignored cache.

**The effective exchange rate file carries two frequencies at once.**  It
contains a daily block (`YYYY-MM-DD`, 1996-04-11 to 2026-10-27) *and* a
monthly block (`YYYY-MM`, 1994-01 to 2026-09) appended after it.  The two
blocks overlap in calendar time.  A parser that accepts both formats puts a
monthly average and a daily observation into the same quarter and neither
number is then what it claims to be.  Only the daily block is read, and the
daily series is resampled to the last observation of each quarter.

**The last quarter of every flow is incomplete.**  A statistical office
publishes what it has, so the current quarter arrives half-finished.  A
quarter is accepted only when the series was observed within ten days of
the quarter end.  Without that rule the current quarter would enter the
factor as if it were whole.

## When the factor cannot be produced

The artefact is written either way.  If the BIS files cannot be read, or if
fewer than forty common quarters are available, the artefact carries
`"status": "unavailable"`, the reason, and the country-panel factor — with
an explicit note that it is a different object.  A missing factor must
never look like a factor that happens to be flat.

## What it does not do

* It does not forecast the global cycle.  The forecast engine works on a
  single country composite.
* It does not claim causal direction.  The factor is a common component of
  published series, not an identified causal driver.
* It does not replace the country layer.  The factor is a global condition;
  the country indices are the local readings.  Neither is derived from the
  other.
