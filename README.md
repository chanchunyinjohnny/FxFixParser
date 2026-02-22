# FxFixParser

A user-friendly tool for parsing FIX (Financial Information eXchange) protocol messages used in FX trading. Paste a raw FIX message and instantly see every tag translated into plain English — no manual spec lookup required.

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
- **Venue-aware parsing** — recognises messages from Smart Trade, FXGO (Bloomberg), 360T, and Bloomberg DOR, including their proprietary custom tags
- **FX product detection** — automatically identifies whether a message is a Spot, Forward, Swap, NDF, Futures, or Options trade
- **Trade summary** — extracts key trade details (symbol, side, quantity, price, settlement date) at a glance
- **Repeating group support** — correctly parses and displays nested groups like market data entries, legs, and party IDs
- **Multiple output formats** — table, human-readable text, and JSON
- **Flexible input** — accepts both standard SOH delimiters and pipe (`|`) delimiters commonly found in logs
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
2. Look up every tag in the FIX 4.4 dictionary (plus venue-specific custom tags)
3. Decode any enumerated values into plain English
4. Detect the trading venue and FX product type
5. Extract a trade summary

### Step 3 — Read the Results

Results are shown in three tabs:

- **Table View** — a sortable table with columns for Tag, Field Name, Description, Value, and Value Description. Repeating groups (e.g. market data entries, trade legs) are displayed in collapsible sections.
- **Human Readable** — a clean text format, useful for copying into emails or documents.
- **JSON** — structured output for programmatic use or further processing.

If the venue is recognised, a **Trade Summary** appears showing the key details at a glance — symbol, side, quantity, price, product type, and settlement information. For quotes, bid/offer prices are shown. For swaps, near and far leg details are broken out separately.

### Sidebar Options

- **Venue** — auto-detected from the SenderCompID, or you can select one manually
- **Strict Checksum Validation** — enable to verify the FIX checksum (tag 10) is correct
- **Strict Body Length Validation** — enable to verify the body length (tag 9) matches
- **Column Visibility** — toggle which columns appear in the table view

### Sample Messages

The sidebar includes built-in sample messages you can load with one click:

| Sample | What It Shows |
|--------|--------------|
| FX Spot | A basic spot execution report |
| FX Forward | Forward trade with settlement date and forward points |
| FX Swap | Swap with near and far leg details |
| FX NDF | Non-deliverable forward with fixing information |
| Market Data Snapshot | Message with repeating group of price entries |
| Market Data Incremental | Incremental market data update |
| Quote Request | Multi-symbol quote request with repeating group |
| FX Swap Quote | TOD/TOM swap quote with all-in rates and swap points |
| Bloomberg DOR Spot | Spot trade via Bloomberg Derivatives Order Routing |
| Bloomberg DOR Forward | Forward trade via Bloomberg DOR |
| Bloomberg DOR Swap | Swap trade via Bloomberg DOR with legs group |

## Supported Venues

| Venue | Description |
|-------|-------------|
| **Smart Trade (LiquidityFX)** | Multi-dealer FX platform with 120+ custom tags covering swap execution, tiered quotes, fixing orders, regulatory tracking, and more |
| **FXGO (Bloomberg)** | Bloomberg's FX trading platform |
| **360T** | Multi-bank FX trading platform |
| **Bloomberg DOR** | Bloomberg Derivatives Order Routing with 47 custom tags for algo execution, tenor support, and multi-leg instruments |

Venue is auto-detected from the SenderCompID (tag 49) in the message. You can also select a venue manually from the sidebar.

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
