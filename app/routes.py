from flask import request, redirect, session, jsonify, render_template
import os
import openai

from .services.spotify import *
from app import app


CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = 'https://python.dextroamphetam1.repl.co/callback'  # 

openai.api_key = os.environ.get('OPENAI_KEY')

@app.route('/spa')
def spa():
    return render_template('index.html')

@app.route('/')
def index():
  # Check if there's an access token in the session
  access_token = session.get('access_token')

  # If the user is already authorized, redirect to the SPA
  if access_token:
    return render_template('index.html')
  
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

@app.route('/callback')
def callback():
  code = request.args.get('code')
  access_token = get_access_token(code)
  # Store the access token in the session
  session['access_token'] = access_token
  # session['refresh_token'] = response_data['refresh_token']

  if access_token:
    return render_template('index.html')

  return "Failed to retrieve access token", 400

@app.route('/create-playlist', methods=['POST'])
def create_playlist_endpoint():
    data = request.json
    song_ids = data.get('song_ids', [])
    playlist_name = data.get('name', 'My Playlist')  # Default name if none provided
    access_token = session.get('access_token')
    user_id = get_user_id(access_token)
    playlist = create_playlist(access_token, user_id, playlist_name)
    add_tracks_to_playlist(access_token, playlist["id"], song_ids)
    return jsonify(playlist)

@app.route('/search')
def search_endpoint():
  query = request.args.get('query')
  access_token = session.get('access_token')
  track_data = search_tracks(access_token, query)
  if track_data == "Token expired":
      session.pop('access_token', None)
      return redirect('/')
  elif track_data:
      return jsonify({"songs": track_data})
  return jsonify({"error": "No results found"}), 404

@app.route('/ask', methods=['POST'])
def ask_openai():
    question = request.json.get('question')
    if not question:
        return jsonify({"error": "Question not provided"}), 400

    response = openai.Completion.create(
      engine="davinci",
      prompt=question,
      max_tokens=150
    )

    return jsonify({"response": response.choices[0].text.strip()})