# FxFixParser

A FIX 4.4 protocol parser for FX trading messages.

## Features

- Parse FIX 4.4 messages for FX trading
- Support for multiple venues: Smart Trade, FXGO, 360T
- Support for FX products: Spot, Forward, Swap, NDF, Futures, Options
- Human-readable tag translation
- Streamlit UI for easy message parsing
- Comprehensive tag dictionary with enumerated value descriptions

## Prerequisites

- Python 3.13 or higher
- pip (Python package manager)

## Quick Start

### 1. Set Up Virtual Environment

```bash
# Navigate to project directory
cd FxFixParser

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 2. Install the Package

```bash
# Install with all dependencies
pip install -e ".[dev]"
```

### 3. Run the Application

```bash
# Start the Streamlit UI
streamlit run src/fxfixparser/ui/app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## Using the Streamlit UI

### Parsing a FIX Message

1. **Paste your FIX message** in the text area
   - Supports both SOH (`\x01`) and pipe (`|`) delimiters

2. **Click "Parse Message"** to analyze the message

3. **View results** in three formats:
   - **Table View**: Shows all fields in a sortable table with Tag, Name, Value, and Description columns
   - **Human Readable**: Text format with field names and value descriptions
   - **JSON**: Structured JSON output for programmatic use

### Using Sample Messages

1. Click **"Sample Messages"** in the sidebar
2. Expand the section and click any sample to load it
3. Available samples:
   - FX Spot (Execution Report)
   - FX Forward
   - FX Swap
   - FX NDF

### Configuration Options

In the sidebar, you can enable:
- **Strict Checksum Validation**: Validates the FIX checksum (tag 10)
- **Strict Body Length Validation**: Validates body length (tag 9)

## Sample FIX Messages

Use these sample messages to test the parser:

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

## Python API Usage

### Basic Parsing

```python
from fxfixparser import FixParser, ParserConfig

# Create parser with default settings (non-strict checksum)
config = ParserConfig(strict_checksum=False)
parser = FixParser(config=config)

# Parse a FIX message
raw_message = "8=FIX.4.4|9=100|35=8|49=FXGO|56=CLIENT|55=EUR/USD|54=1|32=1000000|31=1.0850|10=123|"
message = parser.parse(raw_message)

# Access message properties
print(f"FIX Version: {message.begin_string}")   # FIX.4.4
print(f"Message Type: {message.msg_type}")       # 8 (Execution Report)
print(f"Sender: {message.sender_comp_id}")       # FXGO
print(f"Target: {message.target_comp_id}")       # CLIENT
```

### Accessing Fields

```python
# Get a specific field by tag number
symbol_field = message.get_field(55)
if symbol_field:
    print(f"Tag: {symbol_field.tag}")              # 55
    print(f"Name: {symbol_field.name}")            # Symbol
    print(f"Value: {symbol_field.raw_value}")      # EUR/USD

# Get field with enumerated value description
side_field = message.get_field(54)
if side_field:
    print(f"Side: {side_field.raw_value}")         # 1
    print(f"Description: {side_field.value_description}")  # Buy

# Get typed value (automatic type conversion)
qty_field = message.get_field(32)
if qty_field:
    print(f"Quantity: {qty_field.typed_value}")    # 1000000.0 (float)
```

### Output Formats

```python
# Human-readable format
print(message.to_human_readable())
# Output:
# FIX Message: FIX.4.4
# Message Type: 8
# --------------------------------------------------
# BeginString (8): FIX.4.4
# BodyLength (9): 100
# MsgType (35): 8 (ExecutionReport)
# Symbol (55): EUR/USD
# Side (54): 1 (Buy)
# ...

# JSON/Dictionary format
import json
print(json.dumps(message.to_dict(), indent=2))
```

### Venue Detection

```python
from fxfixparser.venues.registry import VenueRegistry

# Create venue registry
venue_registry = VenueRegistry.default()

# Detect venue from message
venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
if venue_handler:
    print(f"Detected Venue: {venue_handler.name}")  # FXGO

    # Enhance message with venue info
    message = venue_handler.enhance_message(message)

    # Extract trade details
    trade = venue_handler.extract_trade(message)
    print(f"Symbol: {trade.symbol}")
    print(f"Side: {trade.side}")
    print(f"Quantity: {trade.quantity}")
    print(f"Price: {trade.price}")
```

### Product Type Detection

```python
from fxfixparser.products.base import ProductRegistry

# Create product registry
product_registry = ProductRegistry.default()

# Detect product type
product_handler = product_registry.detect(message)
if product_handler:
    print(f"Product Type: {product_handler.product_type}")  # Spot, Forward, Swap, etc.

    # Get product-specific details
    details = product_handler.extract_details(message)
    print(details)
```

### Iterating Over Fields

```python
# Iterate over all fields
for field in message:
    print(f"{field.name} ({field.tag}): {field.raw_value}")

# Get total number of fields
print(f"Total fields: {len(message)}")
```

## Common FIX Tags Reference

| Tag | Name | Description |
|-----|------|-------------|
| 8 | BeginString | FIX protocol version |
| 9 | BodyLength | Message body length |
| 35 | MsgType | Message type (8=ExecutionReport, D=NewOrderSingle) |
| 49 | SenderCompID | Sender company identifier |
| 56 | TargetCompID | Target company identifier |
| 55 | Symbol | Currency pair (e.g., EUR/USD) |
| 54 | Side | 1=Buy, 2=Sell |
| 32 | LastQty | Executed quantity |
| 31 | LastPx | Executed price |
| 15 | Currency | Trade currency |
| 64 | SettlDate | Settlement date |
| 10 | CheckSum | Message checksum |

## Supported Venues

| Venue | SenderCompID Values |
|-------|---------------------|
| Smart Trade | SMARTTRADE, SMTRADE, ST |
| FXGO (Bloomberg) | FXGO, BLOOMBERG, BBG, BFXGO |
| 360T | 360T, THREESIXTYT, 360TGTX |

## Supported Products

| Product | Detection Criteria |
|---------|-------------------|
| Spot | SettlType=0,1,2,3,C or SecurityType=FXSPOT |
| Forward | SettlType=6,B or SecurityType=FXFWD or has forward points |
| Swap | SecurityType=FXSWAP or OrdType=G or has both SettlDate and SettlDate2 |
| NDF | SecurityType=FXNDF or has NDF fixing tags |
| Futures | SecurityType=FUT or has MaturityMonthYear with exchange |
| Options | SecurityType=OPT or has PutOrCall/StrikePrice tags |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=fxfixparser

# Run specific test file
pytest tests/unit/test_parser.py
```

### Code Quality

```bash
# Lint code
ruff check src tests

# Type check
mypy src
```

## Troubleshooting

### Common Errors

**ParseError: Empty message**
- Ensure your FIX message is not empty or whitespace only

**ValidationError: Message must start with BeginString (tag 8)**
- FIX messages must begin with `8=FIX.4.4` (or similar version)

**ValidationError: Message must end with CheckSum (tag 10)**
- FIX messages must end with the checksum field `10=XXX`

**ChecksumError: Checksum mismatch**
- Disable strict checksum validation in settings, or fix the checksum value

### Delimiter Issues

The parser automatically handles both delimiters:
- SOH (ASCII 0x01): Standard FIX delimiter
- Pipe (`|`): Human-readable delimiter commonly used in logs

## Support This Project

If you find FxFixParser useful, consider supporting its development:

- [GitHub Sponsors](https://github.com/sponsors/chanchunyinjohnny)
- [Buy Me a Coffee](https://buymeacoffee.com/chanchunyinjohnny)
- [Ko-fi](https://ko-fi.com/chanchunyinjohnny)

## License

MIT License - Chan Chun Yin Johnny
