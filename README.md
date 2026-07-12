# Strava API Scraper

Original script : https://github.com/odontomachus/stravalib_demo

## Description

This script uses the Strava API to fetch your activities and generate maps, heatmaps, popular segments and
training block reports from them. The "login.py" script authenticates with the Strava API and saves the
access token to `strava.cfg`. The "main.py" script reads that token, syncs your activities to a local cache,
and generates the outputs you ask for.

## Installation

Install the required packages with the following command:

```bash
pip install -r requirements.txt
```

Create an API application here : https://www.strava.com/settings/api

Copy the strava.cfg.sample to strava.cfg and fill the informations in there - DO NOT FILL THE TOKEN VALUE

## Usage

Run the "main.py" script to get started. With no arguments, it syncs your activities and generates every
output (full map, weighted map, heatmap, popular segments, training blocks):

```bash
python main.py
```

Or pick specific outputs:

```bash
python main.py --full-map --heatmap        # only these two maps
python main.py --segments 10               # top 10 popular segments only
python main.py --training-blocks           # training blocks leading up to races only
python main.py --no-fetch --full-map       # reuse the local cache, don't hit the Strava API
python main.py --refresh                   # re-fetch and overwrite every cached activity
python main.py --no-browser                # don't auto-open generated maps
```

Run `python main.py --help` for the full list of options.

Activities are cached in `cache/` as JSON files, so subsequent runs only fetch new activities from Strava.
If you have cache files from an older version of this script (`cache/map-*.json`, polyline-only), they are
picked up automatically to avoid re-fetching polylines - run once with `--refresh` if you also want segment
and training data backfilled for those activities.

## Features

- [x] Global map with all activities
- [x] Weighted map per coordinate
- [x] Heatmap of all activities
- [x] Most popular segments
- [x] Training blocks: activities leading up to a "race" workout, with no gap longer than a week
