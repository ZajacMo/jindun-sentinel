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
| `cycle.json` | the global cycle factor with its loadings |
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

## The global cycle factor

The global cycle is the component of the country stress indices that moves
together.  It is the first principal component of the aligned country
composites — the same construction the country layer uses for its sub-market
indices.

The factor is reported with its loadings and its explained variance, because
a factor that explains a tenth of the variance is a different statement from
one that explains half of it.

The sign of a principal component is arbitrary, so the factor is oriented to
correlate positively with the mean of the country composites.  Without that,
two runs of the same data could report opposite signs and a reader would have
to guess which direction is "more stress".

When the first component explains less than 30 % of the common variance the
artefact says so explicitly: the country stress indices are then not dominated
by a single global driver, and the factor should not be read as one.

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
