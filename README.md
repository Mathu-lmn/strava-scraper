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

Copy the strava.cfg.sample to strava.cfg and fill the informations in there.

## Usage

Run the "login.py" script to authenticate with the Strava API and save the access token to a file:

```bash
python login.py
```

Run the "main.py" script to read the access token from the file and use it to make a request to the Strava API to get data on the user's activities:

```bash
python main.py
```
