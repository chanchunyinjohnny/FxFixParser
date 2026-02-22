# Technical Details

Developer reference for integrating FxFixParser into Python code, understanding the architecture, and contributing to the project.

## Python API Usage

### Basic Parsing

```python
from fxfixparser import FixParser, ParserConfig

# Create parser (non-strict checksum is lenient with log-extracted messages)
config = ParserConfig(strict_checksum=False)
parser = FixParser(config=config)

# Parse a FIX message
raw = "8=FIX.4.4|9=100|35=8|49=FXGO|56=CLIENT|55=EUR/USD|54=1|32=1000000|31=1.0850|10=123|"
message = parser.parse(raw)

# Access message properties
message.begin_string    # "FIX.4.4"
message.msg_type        # "8" (Execution Report)
message.sender_comp_id  # "FXGO"
message.target_comp_id  # "CLIENT"
```

### Accessing Fields

```python
# Get a field by tag number
symbol = message.get_field(55)
symbol.tag              # 55
symbol.name             # "Symbol"
symbol.raw_value        # "EUR/USD"

# Enumerated values are decoded automatically
side = message.get_field(54)
side.raw_value          # "1"
side.value_description  # "Buy"

# Typed values (auto-converted from strings)
qty = message.get_field(32)
qty.typed_value         # 1000000.0 (float)
```

### Output Formats

```python
# Human-readable text
print(message.to_human_readable())
# FIX Message: FIX.4.4
# Message Type: 8
# --------------------------------------------------
# BeginString (8): FIX.4.4
# MsgType (35): 8 (ExecutionReport)
# Symbol (55): EUR/USD
# Side (54): 1 (Buy)
# ...

# Dictionary / JSON
import json
print(json.dumps(message.to_dict(), indent=2))

# Iterate over fields
for field in message:
    print(f"{field.name} ({field.tag}): {field.raw_value}")
```

### Venue Detection and Trade Extraction

```python
from fxfixparser.venues.registry import VenueRegistry

venue_registry = VenueRegistry.default()

# Auto-detect venue from SenderCompID
venue_handler = venue_registry.get_by_sender_id(message.sender_comp_id)
if venue_handler:
    print(venue_handler.name)  # "FXGO"

    # Enhance message with venue-specific tag definitions
    message = venue_handler.enhance_message(message)

    # Extract structured trade details
    trade = venue_handler.extract_trade(message)
    trade.symbol    # "EUR/USD"
    trade.side      # "Buy"
    trade.quantity  # 1000000.0
    trade.price     # 1.085
```

### Product Type Detection

```python
from fxfixparser.products.base import ProductRegistry

product_registry = ProductRegistry.default()
product_handler = product_registry.detect(message)
if product_handler:
    product_handler.product_type  # "Spot", "Forward", "Swap", etc.
    details = product_handler.extract_details(message)
```

### Parser Configuration

```python
config = ParserConfig(
    strict_checksum=True,      # Validate tag 10 (default: True)
    strict_body_length=False,  # Validate tag 9 (default: False)
    strict_delimiter=False,    # Require SOH after each field (default: False)
    allow_pipe_delimiter=True, # Accept | as delimiter (default: True)
)
```

## Architecture

```
src/fxfixparser/
├── core/                  # Parser engine
│   ├── parser.py          # FIX message parsing and validation
│   ├── message.py         # FixMessage and FixField data models
│   ├── field.py           # Field definitions and type system
│   └── exceptions.py      # ParseError, ChecksumError, ValidationError
├── products/              # FX product type handlers
│   ├── base.py            # ProductHandler base class and registry
│   ├── spot.py            # Spot detection
│   ├── forward.py         # Forward detection
│   ├── swap.py            # Swap detection
│   ├── ndf.py             # NDF detection
│   ├── options.py         # Options detection
│   └── futures.py         # Futures detection
├── venues/                # Venue-specific handlers
│   ├── base.py            # VenueHandler abstract base
│   ├── registry.py        # Venue registry and auto-detection
│   ├── smart_trade.py     # LiquidityFX (123 custom tags)
│   ├── fxgo.py            # Bloomberg FXGO
│   ├── three_sixty_t.py   # 360T
│   └── bloomberg_dor.py   # Bloomberg DOR (47 custom tags)
├── tags/                  # Tag dictionaries
│   ├── dictionary.py      # TagDictionary manager
│   ├── fix44.py           # Curated FIX 4.4 tag definitions
│   ├── fx_tags.py         # FX-specific custom tags
│   └── repeating_groups.py
├── spec/                  # FIX specifications
│   ├── loader.py          # QuickFIX XML spec parser
│   ├── FIX44.xml          # FIX 4.4 specification
│   └── FIX50SP2.xml       # FIX 5.0 SP2 specification
└── ui/
    └── app.py             # Streamlit web application
```

### Tag Resolution Order

Tags are resolved through a 3-tier hierarchy:

1. **FIX 4.4 XML specification** — comprehensive base covering all standard tags
2. **Curated FIX 4.4 definitions** (`fix44.py`) — improved descriptions for FX-relevant fields
3. **Venue-specific custom tags** — proprietary tags from Smart Trade, Bloomberg DOR, etc.

Higher tiers override lower ones, so venue-specific definitions take precedence.

### Product Detection Order

Products are checked in order of specificity (most specific first):

1. Swap (SecurityType=FXSWAP, or OrdType=G, or has both SettlDate + SettlDate2)
2. NDF (SecurityType=FXNDF, or has fixing tags 5709/5711)
3. Options (SecurityType=OPT, or has PutOrCall/StrikePrice)
4. Futures (SecurityType=FUT, or has MaturityMonthYear + Exchange)
5. Forward (SecurityType=FXFWD, or SettlType=6/B, or has forward points)
6. Spot (default fallback)

### Venue SenderCompID Mappings

| Venue | Recognised SenderCompID Values |
|-------|-------------------------------|
| Smart Trade | `SMARTTRADE`, `SMTRADE`, `ST`, `LFX_CORE`, `LFX`, `UAT.ATP.RFS.MKT` |
| FXGO | `FXGO`, `BLOOMBERG`, `BBG`, `BFXGO` |
| 360T | `360T`, `THREESIXTYT`, `360TGTX` |
| Bloomberg DOR | `BLOOMBERG_DOR`, `BBGDOR`, `DOR`, `FXOM`, `ORP` |

## Common FIX Tags Reference

| Tag | Name | Description |
|-----|------|-------------|
| 8 | BeginString | FIX protocol version (e.g. FIX.4.4) |
| 9 | BodyLength | Message body length in bytes |
| 35 | MsgType | Message type (8=ExecutionReport, D=NewOrderSingle, S=Quote) |
| 49 | SenderCompID | Sender identifier (used for venue detection) |
| 56 | TargetCompID | Target identifier |
| 55 | Symbol | Currency pair (e.g. EUR/USD) |
| 54 | Side | 1=Buy, 2=Sell |
| 32 | LastQty | Executed quantity |
| 31 | LastPx | Executed price |
| 15 | Currency | Trade currency |
| 64 | SettlDate | Settlement date (YYYYMMDD) |
| 63 | SettlType | Settlement type (0=Regular, 1=Cash, 6=Future) |
| 167 | SecurityType | Security type (FXSPOT, FXFWD, FXSWAP, FXNDF, OPT, FUT) |
| 194 | LastSpotRate | Spot rate for forward trades |
| 195 | LastForwardPoints | Forward points |
| 193 | SettlDate2 | Far leg settlement date (swaps) |
| 192 | OrderQty2 | Far leg quantity (swaps) |
| 120 | SettlCurrency | Settlement currency (NDFs) |
| 10 | CheckSum | Message checksum (3-digit modulo-256) |

## Supported Type Conversions

| FIX Type | Python Type |
|----------|-------------|
| INT, LENGTH, SEQNUM, NUMINGROUP | `int` |
| FLOAT, PRICE, QTY, AMT, PERCENTAGE, PRICEOFFSET | `float` |
| BOOLEAN | `bool` (Y/N or 1/0) |
| STRING, CURRENCY, UTCTIMESTAMP, LOCALMKTDATE | `str` |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/unit/test_parser.py
```

### Code Quality

```bash
# Format code
black src tests
isort src tests

# Lint
flake8 src tests

# Type check
mypy src
```

### Deployment

```bash
# Create a clean distribution zip
bash pack.sh
# Output: dist/FxFixParser_YYYYMMDD_HHMMSS.zip
```

The pack script includes only production files (src, entry points, pyproject.toml, README) and excludes tests, dev config, and proprietary files.
