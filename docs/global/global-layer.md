# The global layer

The country layer answers "how stressed is this economy".  The global layer
answers the two questions that follow from it: "**which economies move
together**" and "**who is exposed to whom**".

The global layer is deliberately built from the *same* methods as the country
layer, one level up.  That is not a stylistic choice: it is what makes the two
layers comparable, and it is what makes a statement like "the euro area is
currently transmitting more stress to the United Kingdom than China is"
checkable rather than rhetorical.

Four artefacts are produced by `python -m jindun.cli global`:

| Artefact | Content |
| --- | --- |
| `spillover.json` | the cross-country contagion network |
| `cycle.json` | the global financial cycle factor and its country-panel cross-check |
| `banking_network.json` | the cross-border banking network |
| `gsib.json` | the FSB list of global systemically important banks |

## Cross-country contagion

The nodes are the country composites; the edges are the share of one
country's forecast error variance that is attributable to another.  The
estimator is the identical generalised variance decomposition the country
layer uses across its markets, including the four estimators described in
`spillover-legacy-vs-paper.md`.

Two properties decide how the network may be read:

* **The node set changes between runs.**  A network is only comparable with
  another network computed over the same nodes.  This is one reason the
  ordering-sensitive Cholesky estimator is not the default here: it would
  make the comparison meaningless.
* **The countries are compared on their percentile lens.**  A percentile is
  the only quantity comparable across jurisdictions with different indicator
  mixes and different market structures.  The deviation lens is reported
  alongside it as the absolute anchor.

Only the dates on which **every** country has an observation are used.  A
variance decomposition over a ragged panel would silently attribute the
missing days to whichever country happened to be present.

## The global financial cycle factor

`cycle.json` carries two different objects, and they must not be confused.

**The factor (layer L3).**  The first principal component of a standardised
block of BIS series:

| Input | Flow | What it measures |
| --- | --- | --- |
| `global_credit_yoy` | `WS_GLI` | year-on-year growth of cross-border bank claims on non-bank borrowers, all currencies |
| `usd_credit_yoy` | `WS_GLI` | the same for US dollar credit outside the United States |
| `eur_credit_yoy` | `WS_GLI` | the same for euro credit outside the euro area |
| `credit_gap_*` | `WS_CREDIT_GAP` | the credit-to-GDP gap of every monitored economy, in percentage points |
| `eer_us_yoy` | `WS_EER` | year-on-year change of the broad nominal effective exchange rate of the United States |

A global financial cycle in the sense of Bruno & Shin (2014) and
Miranda-Agrippino & Rey (2020) is a *global credit and currency* driver, so
the factor is estimated from those published flows rather than from the
monitored economies' own indices.

**The cross-check (layer L1).**  The first principal component of the aligned
country composites — the aggregate of the monitored stress indices, built the
same way the country layer builds its sub-market indices.  It is the natural
check on the first: the quarterly factor is carried forward onto the daily
calendar of the panel and the two are correlated over the overlap.

Three properties of the factor decide how it may be read, and all three are
stated in the artefact itself:

* **Its sign is anchored on the credit gap.**  The sign of a principal
  component is arbitrary, so the factor is oriented to correlate positively
  with the mean of the standardised credit-to-GDP gaps.  A higher factor then
  means credit is further above its own trend — the configuration that
  precedes financial stress.  It does **not** mean that stress is already
  present.
* **Its window is the window its shortest input allows.**  The euro area's
  credit gap starts in 2009, so the factor starts in 2009 even though the
  credit series themselves go back to the 1950s.
* **Its explained variance is reported.**  The first component explains about
  a third of the variance of the input block, and the artefact says so: these
  flows do not move as one driver, and the factor must not be read as one.
  The loadings are published as well, so a reader can see exactly which
  series carry the component — and which do not.

The full description, including how the BIS files are read and the two
properties of the published data that change how they have to be read, is in
`global-cycle-factor.md`.

## The cross-border banking network

Built from the BIS locational banking statistics — the only public measure of
who lends to whom across borders.  The full description, including why the
bilateral matrix has to come from the bulk archive rather than the API, is in
`banking-network.md`.

## The G-SIB list

The Financial Stability Board's list of global systemically important banks,
parsed from the official PDF publication.  The list is read together with the
banking network: a bank that is systemically important *and* sits on a large
cross-border claim is a different risk object from a bank that is only
important domestically.

The parser follows the structure of the published document — a bucket number,
the surcharge percentage, and the bank names one per line — and the artefact
carries the bucket histogram, so a parsing error that changed the
distribution would be visible.

## What the global layer does not do

* It does not forecast the global cycle.  The forecast engine works on a
  single country composite; a global forecast is a separate piece of work.
* It does not merge the banking network with the contagion network.  The
  first is a *stock of exposures* across borders, the second is a *share of
  forecast error variance* between stress indices; they answer different
  questions and combining them into a single "global risk score" would hide
  both.
* It does not claim causal direction.  A spillover share says how much of one
  node's uncertainty is attributable to another under a specific estimator; it
  is not a statement about who caused what.
