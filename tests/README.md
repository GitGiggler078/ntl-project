# Night Light NTL Extractor

This repository extracts nighttime light (NTL) data for Indian cities using Google Earth Engine and geocoding.

## Purpose

The project loads city coordinates, computes average nighttime light values from the NOAA VIIRS dataset, and writes the results to a CSV file.

## Prerequisites

- Python 3.11 or later
- A working Google Earth Engine account with access configured in your environment
- Optional: `python-dotenv` to load a `.env` file automatically

## Setup

1. Create a virtual environment and activate it:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy the environment example:

```bash
cp .env.example .env
```

4. Update `.env` with your own project values.

## Configuration

The script reads configuration values from environment variables:

- `GEE_PROJECT_ID` — Google Earth Engine project ID
- `START_DATE` — required start date for NTL data filtering (YYYY-MM-DD)
- `END_DATE` — required end date for NTL data filtering (YYYY-MM-DD)
- `CITIES_FILE` — path to a local Python file defining `cities = [...]`
- `CACHE_FILE` — local city coordinates cache file name
- `OUTPUT_FILE` — CSV file path for extracted NTL results
- `ERROR_LOG` — log file name for errors
- `GEOPY_USER_AGENT` — geopy user agent string
- `NOMINATIM_COUNTRY` — country hint for geocoding

## Usage

Run the data extraction script:

```bash
python ntl_to_excel.py
```

The script will save the output CSV to the path set in `OUTPUT_FILE`.

## Evidence

The repository includes an `evidence/` folder for example artifacts and logs. Use this folder to store sample output and evidence of successful runs.

## Testing

Run tests with:

```bash
pytest tests/
```

## CI/CD

This project uses GitHub Actions for continuous integration. Tests run on every push and pull request to the main branch.
