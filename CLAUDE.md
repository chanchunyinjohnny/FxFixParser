# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FxFixParser is a Python project for parsing FIX (Financial Information eXchange) protocol messages.
This project focus on building a robust parser for FIX messages used for FX trading, e.g. Spot, Forwards, Swaps, NDF, Futures, Options.
The program is able to parse venue specific FIX messages and extract relevant trade information.
It currently supports parsing FX messages from Smart Trade, FXGO, and 360T, it is able to translate all the tag message into human readable format, telling users what tag means what.

All features are supported by comprehensive unit tests to ensure reliability and correctness.

The project have a UI that allow users to copy and paste the FIX message and get the parsed result in a readable format.

The FIX version is can support is 4.4, and with the possibility to extend to other versions in the future.

The project is MIT licensed, the author's name is Chan Chun Yin Johnny.

The project will ensure not to have any proprietary or confidential information in the code, documentation, or unit tests.

## Development Environment

- **Python version:** 3.13
- **Virtual environment:** `.venv/`

## Commands

Activate virtual environment:
```bash
source .venv/bin/activate
```

## Project Status

This is a new project skeleton. Key setup tasks needed:
- Create `pyproject.toml` for project configuration
- Add FIX protocol parsing implementation
- Set up testing with pytest
