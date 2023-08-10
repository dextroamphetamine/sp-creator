import requests
import json
import base64
import os
from flask import session, request

CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = 'https://python.dextroamphetam1.repl.co/callback'

def get_access_token(code):
  url = "https://accounts.spotify.com/api/token"
  auth_header = base64.b64encode(
    f"{CLIENT_ID}:{CLIENT_SECRET}".encode('utf-8')).decode('utf-8')
  headers = {"Authorization": f"Basic {auth_header}"}
  data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": REDIRECT_URI
  }
  response = requests.post(url, headers=headers, data=data)
  if response.status_code != 200:
    print("Error getting access token:", response_data)
    return redirect('/')
  
  return response.json()["access_token"]


def get_user_id(access_token):
  url = "https://api.spotify.com/v1/me"
  headers = {"Authorization": f"Bearer {access_token}"}
  response = requests.get(url, headers=headers)
  return response.json()["id"]


def create_playlist(access_token, user_id, playlist_name):
    url = f"https://api.spotify.com/v1/users/{user_id}/playlists"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": playlist_name,
        "public": False  # This makes the playlist private
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    return response.json()

def add_tracks_to_playlist(access_token, playlist_id, track_ids):
  url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
  headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
  }
  data = {"uris": [f"spotify:track:{track_id}" for track_id in track_ids]}
  response = requests.post(url, headers=headers, data=json.dumps(data))
  return response.json()

def search_tracks(access_token, query):
  access_token = session.get('access_token')
  query = request.args.get('query')

  headers = {
      'Authorization': f'Bearer {access_token}'
  }
  response = requests.get(f'https://api.spotify.com/v1/search?q={query}&type=track&limit=10', headers=headers)

  if response.status_code == 401:  # Token expired
    if not refresh_access_token():
        return "Token expired"
    else:  
      access_token = session.get('access_token')
      headers['Authorization'] = f'Bearer {access_token}'
      response = requests.get(f'https://api.spotify.com/v1/search?q={query}&type=track&limit=10', headers=headers)
  
  tracks = response.json()["tracks"]["items"]
  
  results = []
  for track in tracks:
      track_id = track["id"]
      track_name = track["name"]
      # Extracting the artist's name. We'll take the first available artist, as songs can have multiple artists.
      artist_name = track['artists'][0]['name'] if track['artists'] else None
      # Extracting the image URL. We'll take the first available image, which is usually the largest.
      image_url = track['album']['images'][0]['url'] if track['album']['images'] else None
      results.append({"id": track_id, "name": track_name, "artist": artist_name, "image_url": image_url})
  
  return results

def refresh_access_token():
    refresh_token = session.get('refresh_token')
    client_creds = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    headers = {
        "Authorization": f"Basic {client_creds}"
    }

    response = requests.post('https://accounts.spotify.com/api/token', data={
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }, headers=headers)
    
    if response.status_code != 200:
      session.pop('access_token', None)  
      return False

    response_data = response.json()
    session['access_token'] = response_data['access_token']
    return True