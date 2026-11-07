# Python Resilient Data Scraper

This is a demonstration of a robust, zero-dependency Python script designed to extract live data from APIs without failing. 

## The Problem
Most basic scripts break when an API rate-limits the user or goes offline, leaving clients with corrupted files or empty data.

## The Solution
I built a single-file Python script that:
1. **Primary & Fallback APIs:** Attempts to fetch from CoinGecko, but automatically falls back to Binance if the first fails.
2. **Atomic Writes:** Writes data to a temporary file first, then replaces the target file. A crash will never corrupt the output.
3. **Zero Dependencies:** Uses only the Python Standard Library (`urllib`, `json`, `argparse`). No `pip install` required.
4. **Graceful Errors:** Logs failures cleanly and exits with code 1 instead of throwing a traceback.

## How to Run
```bash
python3 sample_scraper.py