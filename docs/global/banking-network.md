# The cross-border banking network

The cross-border banking network answers a question that the country layer
cannot: **who is exposed to whom**.  A stress index says that an economy is
under strain; the banking network says which foreign banking system is holding
the claims that make that strain contagious.

The network is built from the BIS *locational banking statistics* (LBS), which
are the only public measure of bilateral cross-border bank exposure.

## What is measured

The LBS report, for every reporting economy, the positions its banks hold
against the residents of every counterparty economy.  Two positions matter
here:

| Position | BIS code | Meaning |
| --- | --- | --- |
| Total claims | `L_POSITION=C` | what the reporting economy's banks are owed |
| Total liabilities | `L_POSITION=L` | what the reporting economy's banks owe |

The directed edge *lender to borrower* is therefore

```
L_REP_CTY  ->  L_CP_COUNTRY
```

and the net position of that pair is `claims - liabilities`.

## The filter

The BIS bulk file carries every dimension of the flow; the network uses one
slice of it.  The filter is applied in `scripts/extract_bis_network.py` and
recorded in `data/snapshots/bis/lbs_bilateral.meta.json` together with the
hash of the result:

| Dimension | Value | Why |
| --- | --- | --- |
| `FREQ` | `Q` | quarterly stock |
| `L_MEASURE` | `S` | amount outstanding, not a change |
| `L_POSITION` | `C`, `L` | claims and liabilities |
| `L_INSTR` | `A`, `G` | all instruments, and loans and deposits as the narrower interbank channel |
| `L_DENOM` | `TO1` | all currencies, converted to US dollars |
| `L_CURR_TYPE` | `A` | all currency types |
| `L_PARENT_CTY` | `5J` | all countries — the only value the flow accepts here |
| `L_REP_BANK_TYPE` | `A` | all reporting institutions |
| `L_CP_SECTOR` | `A` | all counterparty sectors |
| `L_POS_TYPE` | `N` | cross-border positions |

Two filters deserve a word because they are not obvious:

* **`L_PARENT_CTY=5J`.**  The dimension is the location of the parent of the
  reporting entity, and the published flow only carries the aggregate "all
  countries" for it.  The interesting dimension for a bilateral network is
  `L_REP_CTY`, the reporting economy.
* **`L_CP_SECTOR=A` and `L_REP_BANK_TYPE=A`.**  The network is a statement
  about whole banking systems, not about one sector or one type of
  institution.  The sectoral breakdown is a different product.

## Why the bulk file and not the API

The SDMX service answers the *aggregate* query:

```
https://stats.bis.org/api/v1/data/WS_LBS_D_PUB/Q.S.C.G.USD.A.5J.A.5A.A.US.N
```

which is every reporting economy's claims on the United States.  Asking for a
single reporting economy instead,

```
.../Q.S.C.G.USD.A.5J.A.US.A.US.N
```

answers **404**, even though the data is published: the flow serves the
bilateral matrix only through the bulk file.  This was verified across six
rounds of probes with different denominators, currencies, bank types and
position types; `L_PARENT_CTY` accepts `5J` and nothing else.

The bulk archive is 365 MB and expands to about 18 GB of text, so it is
downloaded once into `data/cache/` (never committed) and streamed into a
filtered snapshot under `data/snapshots/bis/`.

```powershell
python scripts/download_bis_bulk.py       # 365 MB, resumable
python scripts/extract_bis_network.py     # streams the archive, writes the snapshot
python -m jindun.cli global               # builds the network from the snapshot
```

## The euro area

The BIS reports the euro area as an aggregate (`XM`) and its members
separately.  The network folds the member states into the aggregate and
**drops the intra-area positions**: a French bank's claim on a German bank is
not a cross-border exposure of the euro area to the world, and counting it
would make the aggregate look more internationally connected than it is.  The
folding is done in `global_layer/banking_network.py` and is covered by tests.

## What the network reports

* every directed edge with its claims, liabilities and net position;
* per node: the claims extended abroad, the liabilities owed to it, the net
  exposure and its share of the network;
* concentration: the Herfindahl index of the bilateral distribution, the
  largest bilateral position and the largest node share.

Concentration is the number to watch.  A network in which one bilateral pair
holds a third of all cross-border claims is a different risk structure from an
evenly spread one, and the same index level means different things in the two
cases.

## Limitations

* The network is a **stock of exposures**, not a flow of distress.  A large
  claim is not a loss until the counterparty defaults; the network says where
  the exposure *is*, and the country layer says how stressed the counterparty
  *is*.  Reading the two together is the point of the global layer.
* The data is quarterly and lags by roughly one quarter; it is not a
  real-time monitor.
* Reporting coverage is not symmetric: some economies report more
  counterparty detail than others, so the matrix is not perfectly balanced.
  The published figures are therefore gross claims and liabilities, and the
  difference between them for a pair is meaningful only when both sides
  report.
