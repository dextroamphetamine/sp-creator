import requests
import base64
import os
from flask import session
from .openai import ask_openai_for_songs, parse_openai_response

BASE_SPOTIFY_URL = "https://api.spotify.com/v1"
CLIENT_ID = os.environ.get('CLIENT_ID')
CLIENT_SECRET = os.environ.get('CLIENT_SECRET')
REDIRECT_URI = 'https://python.dextroamphetam1.repl.co/callback'

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

def make_spotify_request(endpoint, headers, method='GET', data=None, params=None):
    """
    Make a request to the Spotify API.
    """
    url = f'https://api.spotify.com/v1/{endpoint}'
    response = requests.request(method, url, headers=headers, data=data, params=params)
    
    if response.status_code == 401:  # Token expired
        if not refresh_access_token(session.get('refresh_token')):
            return None
        headers['Authorization'] = f'Bearer {session.get("access_token")}'
        response = requests.request(method, url, headers=headers, data=data, params=params)
    
    return response


def search_artists(query, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = make_spotify_request(f'search?q={query}&type=artist&limit=10', headers=headers)
    if not response or response.status_code != 200:
        return []
    artists_data = response.json()["artists"]["items"]
    artists = [{"id": artist["id"], "name": artist["name"], "image_url": artist['images'][0]['url'] if artist['images'] else None} for artist in artists_data]
    return artists

def get_user_id(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = make_spotify_request("me", headers=headers)
    return response.json()["id"]

def create_playlist(access_token, user_id, playlist_name):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "name": playlist_name,
        "public": False  # This makes the playlist private
    }
    response = requests.post(f'{BASE_SPOTIFY_URL}/users/{user_id}/playlists', headers=headers, json=data)
    return response.json()

def add_tracks_to_playlist(access_token, playlist_id, track_ids):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    data = {"uris": [f"spotify:track:{track_id}" for track_id in track_ids]}
    response = requests.post(f'{BASE_SPOTIFY_URL}/playlists/{playlist_id}/tracks', headers=headers, json=data)
    return response.json()

def get_spotify_track_ids(song_titles, artists, access_token):
    track_ids = []
    headers = {'Authorization': f'Bearer {access_token}'}
    for title, artist in zip(song_titles, artists):
        query = f'track:"{title}" artist:"{artist}"'
        response = make_spotify_request(f'search?q={query}&type=track&limit=1', headers=headers)
        tracks = response.json()['tracks']['items']
        if tracks:
            track_ids.append(tracks[0]['id'])
    return track_ids

def get_audio_features(track_ids, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    track_ids_str = ",".join(track_ids)
    response = make_spotify_request(f'audio-features?ids={track_ids_str}', headers=headers)
    if not response or response.status_code != 200:
        return []
    return response.json()["audio_features"]

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
    average_features = {key: value/num_songs for key, value in summed_features.items()}

    return average_features

def find_songs_matching_profile(average_features, access_token, tolerance=0.1):
    headers = {'Authorization': f'Bearer {access_token}'}
    
    # Fetch top tracks or tracks from specific genres as a sample
    response = requests.get(f"{BASE_SPOTIFY_URL}/browse/top-lists", headers=headers)
    track_ids = [track['id'] for track in response.json().get('tracks', {}).get('items', [])]
    
    # Fetch audio features for these tracks
    track_features = get_audio_features(track_ids, access_token)
    
    # Filter tracks based on our desired audio feature profile
    matching_songs = []
    for features in track_features:
        is_match = all(
            (1 - tolerance) * average_features[key] <= features[key] <= (1 + tolerance) * average_features[key]
            for key in average_features
        )
        if is_match:
            matching_songs.append(features['id'])
    
    return matching_songs

def get_extended_song_recommendations(moods, activities, artists, access_token):
    openai_response = ask_openai_for_songs(moods, activities, artists)
    song_artist_pairs = parse_openai_response(openai_response)
    song_titles = [pair[0] for pair in song_artist_pairs]
    suggested_artists = [pair[1] for pair in song_artist_pairs]

    track_ids = get_spotify_track_ids(song_titles, suggested_artists, access_token)
    audio_features_list = get_audio_features(track_ids, access_token)

    average_features = get_common_audio_profile(audio_features_list)
    additional_songs = find_songs_matching_profile(average_features, access_token)

    combined_songs = song_artist_pairs + additional_songs
    return combined_songs

def get_recommendations_based_on_features(audio_features_list, seed_artists, seed_tracks, access_token, song_count):
    # Calculate the average of the audio features
    avg_features = get_average_audio_features(audio_features_list)

    # Prepare the parameters for the Spotify Recommendations API
    params = {
        'limit': song_count,
        'seed_artists': ','.join(seed_artists[:5]),  # Limit to 5 seed artists
        # Limit to 5 seed tracks
        'target_danceability': avg_features['danceability'],
        'target_energy': avg_features['energy'],
        'target_acousticness': avg_features['acousticness'],
        'target_instrumentalness': avg_features['instrumentalness'],
        'target_valence': avg_features['valence'],
        'target_liveness': avg_features['liveness'],
        'target_tempo': avg_features['tempo']
    }

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    response = make_spotify_request('recommendations', headers=headers, params=params)

    if response.status_code != 200:
        print("Error fetching recommendations:", response.content)
        return []

    recommendations = response.json()["tracks"]
    return recommendations


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
          if not isinstance(features[key], str):
            summed_features[key] += features[key]

    # Calculate the average for each feature
    num_songs = len(audio_features_list)
    avg_features = {key: value / num_songs for key, value in summed_features.items()}

    return avg_features

def refresh_access_token(refresh_token):
    client_creds = base64.b64encode(
        f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    headers = {
        "Authorization": f"Basic {client_creds}",
    }

    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

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

def get_spotify_recommendations(seed_artists):
    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }
    params = {
        "seed_artists": ",".join(seed_artists),
        "limit": 10  # You can adjust the limit as needed
    }
    response = make_spotify_request('https://api.spotify.com/v1/recommendations', headers=headers, params=params)
    return response.get('tracks', [])

def get_song_details_from_spotify(song_title, artist_name):
    headers = {
        "Authorization": f"Bearer {session['access_token']}"
    }
    query = f"{song_title} artist:{artist_name}"
    params = {
        "q": query,
        "type": "track",
        "limit": 1
    }
    
    # Construct the URL with embedded query parameters
    base_url = 'https://api.spotify.com/v1/search'
    query_string = "&".join([f"{key}={value}" for key, value in params.items()])   
    response = make_spotify_request(f"search?{query_string}", headers=headers)
    tracks = response.json()['tracks']['items']
    return tracks[0] if tracks else None

def merge_songs(openai_songs, spotify_songs):
    combined_songs = openai_songs + spotify_songs
    unique_songs = {song['id']: song for song in combined_songs}.values()
    return list(unique_songs)

