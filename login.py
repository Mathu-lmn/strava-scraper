import configparser
import http.server
import os
import time
import webbrowser

from stravalib.client import Client as StravaClient

CONFIG_FILE = "strava.cfg"


class AuthError(Exception):
    pass


class AuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        query = self.path.split("?", 1)[-1]
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)

        if "code" in params:
            self.server.code = params["code"]
            self.server.error = None
            body = b"Authorized, you can close this tab."
        else:
            self.server.code = None
            self.server.error = params.get("error", "no code received")
            body = "Authorization failed: {0}".format(self.server.error).encode()

        self.send_response(200)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def _load_config():
    if not os.path.exists(CONFIG_FILE):
        raise AuthError(
            "{0} not found. Copy strava.cfg.sample to {0} and fill in your API credentials.".format(CONFIG_FILE)
        )

    cfg = configparser.ConfigParser(default_section="Application")
    cfg.read(CONFIG_FILE)

    if not cfg.has_section("StravaClient"):
        raise AuthError("Missing [StravaClient] section in {0}.".format(CONFIG_FILE))

    try:
        client_id = cfg.get("StravaClient", "ClientId")
        client_secret = cfg.get("StravaClient", "ClientSecret")
    except configparser.NoOptionError as e:
        raise AuthError("Missing setting in {0}: {1}".format(CONFIG_FILE, e))

    if not client_id or not client_secret or client_id == "xxxx" or client_secret == "xxxxx":
        raise AuthError("Please set your ClientId and ClientSecret in {0}.".format(CONFIG_FILE))

    return cfg, client_id, client_secret


def _save_tokens(cfg, token, refresh_token, expires_at):
    if not cfg.has_section("UserAcct"):
        cfg.add_section("UserAcct")
    cfg.set("UserAcct", "Token", str(token))
    cfg.set("UserAcct", "RefreshToken", str(refresh_token))
    cfg.set("UserAcct", "ExpiresAt", str(expires_at))
    with open(CONFIG_FILE, "w") as cfg_file:
        cfg.write(cfg_file)


def _authorize(client, cfg, client_id, client_secret):
    try:
        port = int(cfg.get("Application", "Port"))
    except (configparser.NoOptionError, ValueError):
        port = 8888

    try:
        httpd = http.server.HTTPServer(('127.0.0.1', port), AuthHandler)
    except OSError as e:
        raise AuthError("Could not start local server on port {0}: {1}".format(port, e))

    authorize_url = client.authorization_url(
        client_id=client_id,
        redirect_uri='http://127.0.0.1:{0}/authorized'.format(port),
        scope={'read_all', 'profile:read_all', 'activity:read_all'},
    )
    webbrowser.open(authorize_url, new=0, autoraise=True)

    print("Waiting for authorization in your browser...")
    httpd.handle_request()
    code = getattr(httpd, "code", None)
    error = getattr(httpd, "error", None)
    httpd.server_close()

    if error or not code:
        raise AuthError("Strava authorization failed: {0}".format(error or "no code received"))

    token_data = client.exchange_code_for_token(client_id=int(client_id), client_secret=client_secret, code=code)
    token = token_data['access_token']
    refresh_token = token_data['refresh_token']
    expires_at = token_data['expires_at']
    _save_tokens(cfg, token, refresh_token, expires_at)
    return token, refresh_token, expires_at


def login():
    cfg, client_id, client_secret = _load_config()
    client = StravaClient()

    try:
        token = cfg.get("UserAcct", "Token")
    except (configparser.NoSectionError, configparser.NoOptionError):
        token = None

    if not token:
        token, refresh_token, expires_at = _authorize(client, cfg, client_id, client_secret)
    else:
        try:
            expires_at = cfg.get("UserAcct", "ExpiresAt")
            refresh_token = cfg.get("UserAcct", "RefreshToken")
        except configparser.NoOptionError:
            raise AuthError(
                "No RefreshToken/ExpiresAt in {0} but a Token is present. "
                "Please erase the Token value and try again.".format(CONFIG_FILE)
            )

    if int(expires_at) < int(time.time()):
        try:
            token_data = client.refresh_access_token(
                client_id=int(client_id), client_secret=client_secret, refresh_token=refresh_token
            )
        except Exception as e:
            raise AuthError(
                "Failed to refresh Strava token: {0}. Try erasing the Token value in {1}.".format(e, CONFIG_FILE)
            )
        token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        expires_at = token_data['expires_at']
        _save_tokens(cfg, token, refresh_token, expires_at)

    client.access_token = token

    athlete = client.get_athlete()
    print("Successfully authenticated for {0} {1}".format(athlete.firstname, athlete.lastname))

    return client
