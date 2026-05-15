# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

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

# Project Memory & Instructions

## User Preferences

- **Never commit on behalf of the user.** Always let the user review changes before committing. Do not run `git commit` unless explicitly asked.

## Development Environment

- **Python version:** 3.10/3.11 (BOCHK restriction — not 3.13)

## Company Restrictions (BOCHK)

- Python 3.10/3.11 only (not 3.13)
- Streamlit pinned to 1.30
- No ruff, no pytest-cov — use flake8/black/isort instead
- See `proprietary/companyrestriction/bochk.yaml` for full allowed dependency list

## Streamlit 1.30 Compatibility

- `st.dataframe(width="stretch")` does NOT work — use `use_container_width=True` instead
- `st.column_config.*Column(width="small"/"medium"/"large")` not supported — omit the width param
- Always test UI against pinned Streamlit version when making UI changes

## Restrictions

- Use the provided bochk conda environment to run and test the code, do not use local python environment
- Do not install any new pip dependencies, only use the ones already in the bochk environment

## Proprietary / Dev-Only Files

- The `proprietary/` folder is **dev-only reference material** — it will NOT exist in production deployments.
- Never add proprietary files to git. The folder is gitignored.
- Venue-specific XML specs (e.g. Bloomberg ORP) are NOT bundled in the source tree.
- All venue custom tags must be defined in Python code (not loaded from external XML at runtime).
- The `load_fix_spec_fields()` loader exists for bundled public specs (FIX44.xml) only.