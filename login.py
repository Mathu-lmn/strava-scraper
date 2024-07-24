import configparser
import http.server
import webbrowser

# Strava REST API wrapper
from stravalib.client import Client as StravaClient

class AuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Authorized")
        self.get_code()

    def get_code(self):
        self.server.code = [ x[5:]for x in self.path.split("?")[-1].split('&')  if x.startswith('code=') ][0]
        
# Only run this if we call this script directly
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
    
    # if we haven't authorized yet, let's do it:
    if not token:
        # get token from strava
        client_id = cfg.get("StravaClient", "ClientId")
        client_secret = cfg.get("StravaClient", "ClientSecret")
        port = int(cfg.get("Application", "Port"))
        
        # setup webserver for authentication redirect
        httpd = http.server.HTTPServer(('127.0.0.1', port), AuthHandler)

        # The url to authorize from
        authorize_url = client.authorization_url(client_id=client_id, redirect_uri='http://127.0.0.1:{port}/authorized'.format(port=port), scope={'read_all','profile:read_all','activity:read_all'})
        # Open the url in your browser
        webbrowser.open(authorize_url, new=0, autoraise=True)

        # wait until you click the authorize link in the browser
        httpd.handle_request()
        code = httpd.code

        client_id = int(client_id)
        # Get the token
        token = client.exchange_code_for_token(client_id=client_id, client_secret=client_secret, code=code)['access_token']

        # Now store that access token in the config
        cfg.set("UserAcct", "Token", str(token))
        with open("strava.cfg", "w") as cfg_file:
            cfg.write(cfg_file)

    client.access_token = token

    # do stuff
    athlete = client.get_athlete()
    print("Successfully authenticated for {0} {1}".format(athlete.firstname, athlete.lastname))
