# FxFixParser

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fx-fix-parser.streamlit.app/)

A user-friendly tool for parsing FIX (Financial Information eXchange) protocol messages used in FX trading. Paste a raw FIX message and instantly see every tag translated into plain English — no manual spec lookup required.

**Live app:** Try FxFixParser on Streamlit Cloud at [fx-fix-parser.streamlit.app](https://fx-fix-parser.streamlit.app/).

## What Does This Tool Do?

FIX messages are the standard way banks, brokers, and trading platforms communicate trade details electronically. They look like this:

```
8=FIX.4.4|35=8|49=FXGO|55=EUR/USD|54=1|32=1000000|31=1.0850|...
```

These cryptic tag-number pairs are hard to read without constantly referencing the FIX specification. **FxFixParser** translates them into something humans can understand:

| Tag | Field Name | Value | Meaning |
|-----|-----------|-------|---------|
| 35 | MsgType | 8 | Execution Report |
| 55 | Symbol | EUR/USD | |
| 54 | Side | 1 | Buy |
| 32 | LastQty | 1000000 | |
| 31 | LastPx | 1.0850 | |

## Key Features

- **Instant tag translation** — every FIX tag is mapped to its field name and human-readable description
- **Enumerated value decoding** — coded values like `54=1` are decoded to "Buy", `39=2` to "Filled", etc.
- **Venue-aware parsing** — recognises messages from Smart Trade, Bloomberg FXGO, Bloomberg DOR, 360T (RFS Market Taker + SUN swaps order book + TradeImporter), SGX Titan OTC, and LSEG / Refinitiv FX Matching (MAPI), including their proprietary custom tags
- **FX product detection** — automatically identifies whether a message is a Spot, Forward, Swap, NDF, Futures, or Options trade
- **Trade summary** — extracts key trade details (symbol, side, quantity, price, settlement date) at a glance
- **Repeating group support** — correctly parses and displays nested groups like market data entries, legs, and party IDs
- **LEI detection and lookup** — Legal Entity Identifiers found in party/regulatory fields are check-digit validated offline, and can optionally be resolved to legal entity names via the public GLEIF API
- **Multiple output formats** — table, human-readable text, and JSON
- **Flexible input** — accepts standard SOH delimiters, pipe (`|`) delimiters commonly found in logs, and pre-parsed FIX report text (one `(tag)Field: value` per line, as produced by some log viewers) which is reconstructed into the raw message automatically
- **Web UI and CLI** — use whichever suits your workflow

## Quick Start

### Prerequisites

- Python 3.10 or 3.11
- pip (Python package manager)

### Installation

```bash
# Clone or download the project
cd FxFixParser

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS/Linux
# .venv\Scripts\activate         # Windows

# Install the package
pip install -e ".[dev]"
```

### Launch the Web UI

Use the hosted Streamlit app:

[https://fx-fix-parser.streamlit.app/](https://fx-fix-parser.streamlit.app/)

Or run it locally:

```bash
python run_ui.py
# or
streamlit run src/fxfixparser/ui/app.py
```

The app opens in your browser at `http://localhost:8501`.

### Launch the CLI

```bash
# Interactive mode — paste messages one at a time
python run_cli.py

# Parse a single message
python run_cli.py "8=FIX.4.4|35=8|49=FXGO|55=EUR/USD|54=1|32=1000000|31=1.0850|10=123|"

# Read from a file
python run_cli.py -f message.txt

# Pipe from another command
cat message.txt | python run_cli.py

# Choose output format: human (default), table, or json
python run_cli.py -o json "8=FIX.4.4|..."
```

## Using the Web UI

### Step 1 — Paste Your Message

Copy a FIX message from a log file, email, or trading system and paste it into the text area. The parser handles both standard SOH delimiters and pipe (`|`) delimiters, so you can paste it exactly as you see it.

### Step 2 — Parse

Click **"Parse Message"**. The tool will:
1. Split the message into individual fields
2. Look up every tag in the dictionary — FIX 4.4 + FIXT 1.1 session tags + FX extensions by default, with venue-specific custom tags merged in when a venue is detected or selected
3. Decode any enumerated values into plain English
4. Detect the trading venue and FX product type
5. Extract a trade summary

### Step 3 — Read the Results

Results are shown in three tabs:

- **Table View** — a sortable table with columns for Tag, Field Name, Description, Value, and Value Description. Repeating groups (e.g. market data entries, trade legs) are displayed in collapsible sections.
- **Human Readable** — a clean text format, useful for copying into emails or documents.
- **JSON** — structured output for programmatic use or further processing.

If the venue is recognised, a **Trade Summary** appears showing the key details at a glance — symbol, side, quantity, price, product type, and settlement information. For quotes, bid/offer prices are shown. For swaps, near and far leg details are broken out separately. For two-sided swap quotes with per-leg all-in rates (e.g. Bloomberg DOR), the swap points are **computed from the all-in leg rates** (far leg − near leg, per side — the spec definition of swap points) and shown in both pips and rate terms — each side labelled with the price taker's direction (sell-near/buy-far vs buy-near/sell-far), derived from the numbers rather than the venue's Bid/Offer labels — and a **Forward Point Check** table verifies the venue's declared forward-point fields against the points implied by its own all-in and spot rates — flagging whether the venue sent spec-compliant unscaled decimals, market-convention pips, or numbers that simply don't agree with its own rates.

### Sidebar Options

- **Venue** — auto-detected from the SenderCompID, or you can select one manually
- **Strict Checksum Validation** — enable to verify the FIX checksum (tag 10) is correct
- **Strict Body Length Validation** — enable to verify the body length (tag 9) matches
- **LEI Lookup** — when enabled, detected Legal Entity Identifiers are resolved to legal entity names via the public GLEIF API (needs internet access; off by default so the app works fully offline)
- **Column Visibility** — toggle which columns appear in the table view

### LEI Detection & GLEIF Lookup

FIX messages routinely carry ISO 17442 **Legal Entity Identifiers** — in party fields (PartyID 448, PartySubID 523, SettlPartySubID 785, RootPartySubID 1121) or as the UTI generator in RegulatoryTradeIDSource (1905). FxFixParser handles them in two layers:

- **Offline detection & validation (always on):** every LEI-shaped value is detected and its ISO 7064 MOD 97-10 check digits are verified — no network involved. Detected LEIs appear in a dedicated **Legal Entity Identifiers** panel below the parsed output, showing which tags each one was found in and whether its check digits are valid.
- **GLEIF lookup (opt-in):** flip **Look up entity names on GLEIF** in the sidebar and each detected LEI is resolved against the public [GLEIF API](https://www.gleif.org/en/lei-data/gleif-api) — no API key required. The legal name, entity status, jurisdiction and city are added to the panel, and the **Table View shows the raw identifier and the resolved legal name side by side**: the name appears in the Value Description column next to the raw LEI, exactly the way coded values like `54=1` decode to "Buy". With the toggle off, the same column shows the offline check-digit verdict instead.

Lookups are cached for an hour, and failures (no internet, unknown LEI) fall back per-row to the offline view — so the app keeps working on restricted networks.

Example: `523=54930035WQZLGC45RZ35` displays as raw value `54930035WQZLGC45RZ35` with parsed value "The Monetary Authority of Singapore".

### Sample Messages

The sidebar includes built-in sample messages you can load with one click. They
are **grouped by venue** — one expander per venue, in the same order as the venue
selector — so you can see how the same product looks on different interfaces:

| Venue group | What It Shows |
|-------------|--------------|
| Smart Trade (LiquidityFX) | Swap execution, TOD/TOM swap quote with all-in rates and swap points, market data snapshot and incremental update (repeating groups of price entries) |
| Bloomberg FXGO | Spot execution, NDF with fixing information, multi-symbol quote request |
| Bloomberg DOR | Spot, forward and swap executions (legs group), a two-sided swap quote with per-leg all-in rates and forward points, plus a MAP gateway swap with competing dealer quotes and LEIs |
| 360T RFS | Spot quote request, two-way swap quote, forward / swap / NDF executions |
| 360T SUN | Swap limit order, partial fill, NDS, the regulatory 'Trade Export' report, a strip (NewOrderList), a credit-check request, the financial calendar and the swap-points book |
| 360T TI | Post-trade spot / forward / swap executions with competing dealer quotes, money market and option |
| SGX Titan OTC | FX futures trade capture and execution report |
| LSEG FX Matching | Spot execution, forward-swap execution with legs, forward-swap quote negotiation |

## Supported Venues

| Venue | Description |
|-------|-------------|
| **Smart Trade (LiquidityFX)** | Multi-dealer FX platform with 120+ custom tags covering swap execution, tiered quotes, fixing orders, regulatory tracking, and more |
| **Bloomberg FXGO** | Bloomberg's FX trading *platform* — the front-end where FX price discovery and execution happen |
| **Bloomberg DOR** | Bloomberg Derivatives Order Routing — the ORP/DOR FIX *connectivity protocol* (FIXT 1.1 / FIX 5.0 SP2) that carries Bloomberg execution-facility flow; custom tags for algo execution, tenor support, multi-leg instruments, competing dealer quotes, and regulatory trade IDs. Also covers the Bloomberg **MAP gateway** — the same ORP/DOR dialect carried over plain FIX 4.4 with `MAP_<party>` CompIDs |
| **360T RFS (Market Taker)** | Deutsche Börse multi-bank FX RFS platform (FIX 4.4). Spot, Forward, Swap, NDF, NDS, FX Time Option and Block trades across QuoteRequest/Quote/QuoteCancel/NewOrderSingle/NewOrderMultileg/ExecutionReport/SecurityDefinition. Derives product type (no SecurityType is sent) and extracts 360T swap economics — Side relative to the base currency on the far leg, far-leg rates from 6050/6051 quotes and 6160 fills |
| **360T SUN (Swap User Network)** | 360T's anonymous FX Swap limit order book, run as a 360T MTF (FIX 5.0 SP2 over FIXT 1.1). Every instrument is two-legged — FX Swap, NDS and EFP — across NewOrderSingle/NewOrderList (strips)/OrderCancelReplace/ExecutionReport, the regulatory 'Trade Export' ExecutionReport, the PartyRiskLimitCheck credit-check pair, SecurityDefinition (tenor calendar) and the swap-points market data book. Orders are priced in swap points, so the Trade Summary reads the all-in leg rates from 9630/9631 (or 31/6160 on the trade export) and never shows the points as a rate |
| **360T TI (TradeImporter)** | 360T's post-trade STP feed (FIX 4.4). A single ExecutionReport message per filled trade; ProductType (7071) carries the product directly (FX-SPOT/FX-FWD/FX-SWAP/FX-OPTION/MM/…); competing-dealer quotes in NoCompetingQuotes (9516); swap far-leg rate in 6160. Full Trade Summary for the core FX set; all products fully tag-decoded |
| **SGX Titan OTC** | SGX Titan OTC FIX 5.0 SP2 gateway for SGX listed FX futures (KRW/USD, USD/CNH, FlexC variants, etc.) |
| **LSEG / Refinitiv FX Matching (MAPI)** | Anonymous interbank FX Matching central-limit-order-book; FX Spot and FX Forward Swap over FIX 5.0 SP2 / FIXT 1.1, including the forward-swap quote-negotiation messages |

Venue is auto-detected from the message's component IDs — SenderCompID (tag 49), TargetCompID (tag 56), or OnBehalfOfCompID (tag 115) — so client-to-venue messages resolve too (e.g. LSEG FX Matching is recognised by the constant gateway CompID `TR MATCHING`). Bloomberg FXGO and Bloomberg DOR share the Bloomberg umbrella: a DOR/ORP message is recognised by its FIXT 1.1 / FIX 5.0 protocol markers even when it carries a generic Bloomberg CompID, so it is never mistaken for FXGO; MAP gateway sessions are recognised by their `MAP_BLP*` CompID (the Bloomberg side of a MAP session) even though they run plain FIX 4.4 without routing markers. The three 360T interfaces are handled the same way: a TradeImporter message is recognised by its `_TI` CompID, its TI ProductType values, or its NoCompetingQuotes group, and a SUN message by its own dialect markers — a `_SUN` CompID, a SUN-only tag (e.g. LastNearLegPx 9630, UnevenSwapAllowed 9822), the `EMSO-` fill-id prefix, the FX-NDS product code, or a PartyRiskLimitCheck message — so none of them is ever mistaken for another. You can also select a venue manually from the sidebar.

## Supported FIX Versions

The parser is version-agnostic at the byte level — it parses any FIX `tag=value<SOH>` stream regardless of BeginString (FIX 4.2, 4.4, 5.0 SP2, FIXT 1.1 all work structurally). What differs across versions is the tag dictionary used for human-readable translation:

| Dictionary | Coverage | Default? |
|------------|----------|----------|
| **FIX 4.4** | Standard FIX 4.4 fields (loaded from bundled `spec/FIX44.xml`) | Yes |
| **FIXT 1.1 session tags** | 1128 ApplVerID, 1129 CstmApplVerID, 1156 ApplExtID | Yes (merged into default) |
| **FX extensions** | Curated FX-specific tags and enum descriptions | Yes (merged into default) |
| **Venue custom tags** | Smart Trade, Bloomberg FXGO, Bloomberg DOR, 360T RFS, 360T SUN, 360T TI, SGX Titan OTC, LSEG FX Matching | Merged when venue is detected/selected |
| **FIX 5.0 SP2** | Standard FIX 5.0 SP2 fields (bundled `spec/FIX50SP2.xml`) | Auto-loaded when a message carries `1128=9` (ApplVerID); also available via `load_fix_spec_fields()` |

## Supported FX Products

The parser automatically identifies the FX product type from the message content:

| Product | What It Is |
|---------|-----------|
| **Spot** | Immediate currency exchange, settling in T+0 to T+2 |
| **Forward** | Currency exchange at a future date with a locked-in rate |
| **Swap** | Two simultaneous trades — buy one date, sell another (or vice versa) |
| **NDF** | Non-deliverable forward — settled in cash based on a fixing rate, used for restricted currencies |
| **Options** | Right (but not obligation) to exchange currency at a specified strike price |
| **Futures** | Exchange-traded contract for future currency delivery |

## Sample FIX Messages

Use these to try out the parser:

### FX Spot Trade
```
8=FIX.4.4|9=200|35=8|49=FXGO|56=CLIENT|34=1|52=20240115-10:30:00|37=ORD001|17=EXEC001|150=F|39=2|55=EUR/USD|54=1|32=1000000|31=1.0850|15=EUR|64=20240117|60=20240115-10:30:00|10=123|
```

### FX Forward Trade
```
8=FIX.4.4|9=220|35=8|49=360T|56=CLIENT|34=1|52=20240115-10:30:00|37=ORD002|17=EXEC002|150=F|39=2|55=EUR/USD|167=FXFWD|54=1|32=5000000|31=1.0900|15=EUR|64=20240415|194=1.0850|195=0.0050|60=20240115-10:30:00|10=045|
```

### FX Swap Trade
```
8=FIX.4.4|9=250|35=8|49=SMARTTRADE|56=CLIENT|34=1|52=20240115-10:30:00|37=ORD003|17=EXEC003|150=F|39=2|55=USD/JPY|167=FXSWAP|54=1|32=10000000|31=148.50|15=USD|64=20240117|193=20240415|192=10000000|194=148.50|195=0.50|60=20240115-10:30:00|10=178|
```

### FX NDF Trade
```
8=FIX.4.4|9=230|35=8|49=FXGO|56=CLIENT|34=1|52=20240115-10:30:00|37=ORD004|17=EXEC004|150=F|39=2|55=USD/KRW|167=FXNDF|54=1|32=5000000|31=1320.50|15=USD|64=20240415|120=USD|60=20240115-10:30:00|10=092|
```

## Troubleshooting

### "Parse Error: Empty message"

Make sure you've pasted something into the text area. Whitespace-only input won't parse.

### "Message must start with BeginString (tag 8)"

FIX messages must begin with `8=FIX.4.4` (or another version string). If your log snippet starts mid-message, add the header tags.

### "Message must end with CheckSum (tag 10)"

FIX messages must end with a checksum field like `10=123|`. If your log is truncated, append a dummy checksum: `10=000|`.

### "Checksum mismatch"

The checksum in the message doesn't match the calculated value. This is common when messages are hand-edited or extracted from logs. Disable **Strict Checksum Validation** in the sidebar to skip this check.

### Delimiter issues

The parser handles both standard SOH (ASCII 0x01) and pipe (`|`) delimiters automatically. No configuration needed — just paste your message as-is.

## Support This Project

If you find FxFixParser useful, consider supporting its development:

- [GitHub Sponsors](https://github.com/sponsors/chanchunyinjohnny)
- [Buy Me a Coffee](https://buymeacoffee.com/chanchunyinjohnny)
- [Ko-fi](https://ko-fi.com/chanchunyinjohnny)

## License

MIT License - Chan Chun Yin Johnny

---

For Python API usage, architecture details, and development setup, see [TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md).
