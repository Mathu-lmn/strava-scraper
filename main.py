import configparser
import webbrowser

# Strava REST API wrapper
from stravalib.client import Client as StravaClient

        
if __name__ == "__main__":

    # Let's load the config from a file
    cfg = configparser.ConfigParser(default_section="Application")
    cfg.read("strava.cfg")

    # Load credentials
    try:
        token = cfg.get("UserAcct", "Token")
    except configparser.NoOptionError:
        token = None

    # get a strava client
    client = StravaClient()
    
    if not token:
        print("Please run the login.py script first to authenticate")
        exit()

    client.access_token = token

    activities = client.get_activities()
    print("Found {0} activities".format(len(list(activities))))
    for activity in activities:
        print(activity.name)
