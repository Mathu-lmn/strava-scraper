# Strava API Scraper

Original script : https://github.com/odontomachus/stravalib_demo

## Description

This script is a simple example of how to use the Strava API. The "login.py" script will authenticate with the Strava API and save the access token to a file. The "main.py" script will read the access token from the file and use it to make a request to the Strava API to get data on the user's activities.

## Installation

Install the required packages with the following command:

```bash
pip install -r requirements.txt
```

Create an API application here : https://www.strava.com/settings/api

Copy the strava.cfg.sample to strava.cfg and fill the informations in there - DO NOT FILL THE TOKEN VALUE

## Usage

Run the "main.py" script to get started

```bash
python main.py
```


## TODO :
- [x] Global map with all activities
- [x] Weighted per coordinate
- [ ] Improve the map with ponderation by vectorizing instead of plotting each point
- [ ] Get most popular segments
- [ ] Get all trainings until a "race" type, with no pause longer than 1 week
