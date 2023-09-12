import base64
import os
from typing import Dict, Optional

import requests
from flask import session

BASE_SPOTIFY_URL = "https://api.spotify.com/v1/"
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
BASE_FLASK_URI = 'http://127.0.0.1:8080'
BASE_URI = 'http://127.0.0.1:5173'
REDIRECT_URI = f'{BASE_FLASK_URI}/callback'


def get_spotify_auth(code):
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
    response_data = response.json()
    print("Error getting access token:", response_data)
    return None, None

  response_data = response.json()
  return response_data["access_token"], response_data["refresh_token"]


# Implement make_spotify_request based on the interface
def make_spotify_request(endpoint: str, headers: Dict[str, str], method: str = "GET", params: Optional[Dict] = None, json: Optional[Dict] = None, retries: int = 1) -> Dict:
    url = BASE_SPOTIFY_URL + endpoint
    response = requests.request(method, url, headers=headers, params=params, json=json)
    
    if response.status_code == 401 and retries:
        success = refresh_access_token(session.get('refresh_token'))
        if success:
            headers['Authorization'] = f"Bearer {session['access_token']}"
            return make_spotify_request(endpoint, headers, method=method, params=params, json=json, retries=0)
    
    response.raise_for_status()
    return response.json()



def search_artists(query, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = make_spotify_request(f'search?q={query}&type=artist&limit=10', headers=headers)
    
    # Use key lookups instead of dot notation
    if 'artists' not in response or not response['artists']['items']:
        return []
    
    artists_data = response['artists']['items']
    artists = [{
        "id": artist["id"],
        "name": artist["name"],
        "image_url": artist['images'][0]['url'] if artist['images'] else None
    } for artist in artists_data]
    
    return artists


def get_user_id(access_token):
  headers = {"Authorization": f"Bearer {access_token}"}
  response = make_spotify_request("me", headers=headers)
  return response["id"]


def create_playlist(access_token, user_id, playlist_name):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": playlist_name,
        "public": False  # This makes the playlist private
    }
    response = make_spotify_request(f'users/{user_id}/playlists', headers=headers, method="POST", json=data)
    return response

def add_tracks_to_playlist(access_token, playlist_id, track_ids):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {"uris": [f"spotify:track:{track_id}" for track_id in track_ids]}
    response = make_spotify_request(f'playlists/{playlist_id}/tracks', headers=headers, method="POST", json=data)
    return response



def get_spotify_track_ids(song_titles, artists, access_token):
  track_ids = []
  headers = {'Authorization': f'Bearer {access_token}'}
  for title, artist in zip(song_titles, artists):
    query = f'track:"{title}" artist:"{artist}"'
    response = make_spotify_request(f'search?q={query}&type=track&limit=1',
                                    headers=headers)
    tracks = response['tracks']['items']
    if tracks:
      track_ids.append(tracks[0]['id'])
  return track_ids


def get_audio_features(track_ids, access_token):
  headers = {'Authorization': f'Bearer {access_token}'}
  track_ids_str = ",".join(track_ids)
  response = make_spotify_request(f'audio-features?ids={track_ids_str}',
                                  headers=headers)
  if not response:
    return []
  return response["audio_features"]


def get_songs_matching_mood(audio_features, sentiment):
  # Your logic to match songs based on audio features and sentiment
  # This is a placeholder, you can replace it with your actual logic
  matching_songs = []
  for feature in audio_features:
    if feature['valence'] > 0.5 and sentiment == 'positive':
      matching_songs.append(feature['id'])
    elif feature['valence'] <= 0.5 and sentiment == 'negative':
      matching_songs.append(feature['id'])
  return matching_songs


def get_common_audio_profile(audio_features_list):
  summed_features = {feature: 0 for feature in audio_features_list[0]}

  for features in audio_features_list:
    for key, value in features.items():
      if not isinstance(value, str):
        summed_features[key] += value

  num_songs = len(audio_features_list)
  average_features = {
    key: value / num_songs
    for key, value in summed_features.items()
  }

  return average_features


def find_songs_matching_profile(average_features, access_token, tolerance=0.1):
  headers = {'Authorization': f'Bearer {access_token}'}

  # Fetch top tracks or tracks from specific genres as a sample
  response = requests.get(f"{BASE_SPOTIFY_URL}/browse/top-lists",
                          headers=headers)
  track_ids = [
    track['id']
    for track in response.json().get('tracks', {}).get('items', [])
  ]

  # Fetch audio features for these tracks
  track_features = get_audio_features(track_ids, access_token)

  # Filter tracks based on our desired audio feature profile
  matching_songs = []
  for features in track_features:
    is_match = all((1 - tolerance) * average_features[key] <= features[key] <=
                   (1 + tolerance) * average_features[key]
                   for key in average_features)
    if is_match:
      matching_songs.append(features['id'])

  return matching_songs


def get_recommendations_based_on_features(features, seed_artists=None, seed_tracks=None, genres=None, num_songs=10):
    headers = {"Authorization": f"Bearer {session['access_token']}"}

    features = get_average_audio_features(features)

    params = {
        "market": "CA",
        "limit": num_songs,
        "target_acousticness": features.get("acousticness"),
        "target_danceability": features.get("danceability"),
        "target_duration_ms": features.get("duration_ms"),
        "target_energy": features.get("energy"),
        "target_instrumentalness": features.get("instrumentalness"),
        "target_key": round(features.get("key")),  # Round the key value
        "target_liveness": features.get("liveness"),
        "target_loudness": features.get("loudness"),
        "target_popularity": features.get("popularity"),
        "target_speechiness": features.get("speechiness"),
        "target_tempo": features.get("tempo"),
        "target_time_signature": round(features.get("time_signature")),
        "target_valence": features.get("valence")
    }

    params = {k: v for k, v in params.items() if v is not None}

    if seed_artists:
        params["seed_artists"] = ",".join(seed_artists[:5])  # Limit to 5 seed artists

    remaining_seeds = 5 - len(params.get("seed_artists", "").split(","))
  
    if seed_tracks and remaining_seeds > 0:
        params["seed_tracks"] = ",".join(seed_tracks[:remaining_seeds])

    response = make_spotify_request("recommendations", headers=headers, params=params)
    return response.get("tracks", [])


def get_average_audio_features(audio_features_list):
    """
    Compute the average audio features from a list of audio features.
    """
    # Initialize a dictionary to store the sum of each feature
    summed_features = {
        'acousticness': 0,
        'danceability': 0,
        'energy': 0,
        'instrumentalness': 0,
        'key': 0,
        'liveness': 0,
        'loudness': 0,
        'mode': 0,
        'speechiness': 0,
        'tempo': 0,
        'valence': 0,
        'time_signature': 0
    }

    # Sum up all the features
    for features in audio_features_list:
        for key in summed_features:
            if features[key] is not None and not isinstance(features[key], str):
                summed_features[key] += features[key]

    # Calculate the average for each feature and round to 2 decimal places
    num_songs = len(audio_features_list)
    avg_features = {
        key: round(value / num_songs, 2)
        for key, value in summed_features.items()
    }

    return dict(filter(lambda item: item[1] is not None, avg_features.items()))


def refresh_access_token(refresh_token):
  client_creds = base64.b64encode(
    f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

  headers = {
    "Authorization": f"Basic {client_creds}",
  }

  data = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}

  response = requests.post('https://accounts.spotify.com/api/token',
                           data=data,
                           headers=headers)

  if response.status_code != 200:
    session.pop('access_token', None)
    return False

  response_data = response.json()
  session['access_token'] = response_data['access_token']
  return True


def get_artist_ids_from_names(artist_names, access_token):
  artist_ids = []
  for name in artist_names:
    search_results = search_artists(name, access_token)
  for artist in search_results:
    artist_ids.append(artist['id'])

  return artist_ids


def get_song_details_from_spotify(song_title, artist_name):
  headers = {"Authorization": f"Bearer {session['access_token']}"}
  query = f"{song_title} artist:{artist_name}"
  params = {"q": query, "type": "track", "limit": 1}

  # Construct the URL with embedded query parameters
  base_url = 'https://api.spotify.com/v1/search'
  query_string = "&".join([f"{key}={value}" for key, value in params.items()])
  response = make_spotify_request(f"search?{query_string}", headers=headers)
  tracks = response['tracks']['items']
  return tracks[0] if tracks else None


def merge_songs(openai_songs, spotify_songs):
  combined_songs = openai_songs + spotify_songs
  unique_songs = {song['id']: song for song in combined_songs}.values()
  return list(unique_songs)


def filter_songs_by_artist_gender(songs, gender):
  filtered_songs = []
  for song in songs:
    artist_id = song["artists"][0]["id"]
    artist_details = get_artist_details(artist_id)
    if gender == "male" and artist_details["gender"] == "male":
      filtered_songs.append(song)
    elif gender == "female" and artist_details["gender"] == "female":
      filtered_songs.append(song)
  return filtered_songs


def get_artist_details(artist_id):
  headers = {"Authorization": f"Bearer {session['access_token']}"}
  response = make_spotify_request(f"artists/{artist_id}", headers=headers)
  return response

def get_available_genres_from_spotify(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = make_spotify_request('recommendations/available-genre-seeds', headers=headers)
    return response.get('genres', [])

# def get_artist_gender(artist_id: str, spotify_access_token: str) -> Dict:
#     # Define headers for Spotify and MusicBrainz requests
#     spotify_headers = {
#         "Authorization": f"Bearer {spotify_access_token}"
#     }
#     musicbrainz_headers = {}
#
#     # Fetch artist's name from Spotify
#     artist_data = make_spotify_request(f"artists/{artist_id}", spotify_headers)
#     artist_name = artist_data.get('name')
#
#     # Fetch artist's gender from MusicBrainz using the artist's name
#     artist_gender_data = make_musicbrainz_request(f"artist/?query=artist:{artist_name}&fmt=json", musicbrainz_headers)
#     artists = artist_gender_data.get('artists', [])
#
#     if artists:
#         gender = artists[0].get('gender', 'unknown')
#         return {"name": artist_name, "gender": gender}
#     else:
#         return {"error": "Artist not found in MusicBrainz"}
