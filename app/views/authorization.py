from os import environ

from flask import Blueprint, session, request, redirect, jsonify

from ..services.spotify import get_spotify_auth

BASE_FLASK_URI = 'http://127.0.0.1:8080'
BASE_URI = 'http://127.0.0.1:5173'
CLIENT_ID = environ.get('CLIENT_ID')
CLIENT_SECRET = environ.get('CLIENT_SECRET')
REDIRECT_URI = f'{BASE_FLASK_URI}/callback'

auth_blueprint = Blueprint('auth', __name__)

def redirect_to_app():
    return redirect(f"{BASE_URI}")

@auth_blueprint.route("/is-logged-in")
def is_logged_in():
    return jsonify({"isLoggedIn": "access_token" in session})

@auth_blueprint.route('/login')
def index():
    access_token = session.get('access_token')
    refresh_token = session.get('refresh_token')
    # if access_token and refresh_token:
    #     return redirect_to_app()
    auth_url = "https://accounts.spotify.com/authorize"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "playlist-modify-private"
    }
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])
    full_url = f"{auth_url}?{query_string}"
    return redirect(full_url)

@auth_blueprint.route('/callback')
def callback():
    code = request.args.get('code')
    [access_token, refresh_token] = get_spotify_auth(code)
    session['access_token'] = access_token
    session['refresh_token'] = refresh_token
    if access_token:
        return redirect_to_app()
    return "Failed to retrieve access token", 400
