from flask import Blueprint, request, jsonify, session

from ..services.openai_service import (ask_openai_for_songs, parse_openai_response,
                                       ask_openai_to_classify_gender_and_filter_songs)
from ..services.spotify import get_user_id, create_playlist, add_tracks_to_playlist, get_spotify_track_ids, \
    get_audio_features, search_artists, get_recommendations_based_on_features, \
    get_artist_ids_from_names, merge_songs, get_song_details_from_spotify, get_available_genres_from_spotify

spotify_blueprint = Blueprint('spotify', __name__)


@spotify_blueprint.route('/create-playlist', methods=['POST'])
def create_playlist_endpoint():
    data = request.json
    song_ids = data.get('songs', [])
    playlist_name = data.get('name', 'My Playlist')
    access_token = session.get('access_token')
    user_id = get_user_id(access_token)
    playlist = create_playlist(access_token, user_id, playlist_name)
    add_tracks_to_playlist(access_token, playlist["id"], song_ids)
    return jsonify(playlist)


@spotify_blueprint.route('/search-songs', methods=['POST'])
def search_songs():
    data = request.json
    moods = data.get('moods', [])
    activities = data.get('activities', [])
    artists = data.get('artists', [])
    song_count = data.get('songCount', 10)
    gender_preference = data.get('genderPreference', None)
    access_token = session.get("access_token")

    # 1. Use OpenAI to get song suggestions based on moods, activities, and artists
    openai_response = ask_openai_for_songs(moods, activities, artists, song_count, None, gender_preference)

    # 2. Parse the OpenAI response to get song titles and artists
    song_artist_pairs = parse_openai_response(openai_response)

    song_titles = [pair[0] for pair in song_artist_pairs]
    suggested_artists = [pair[1] for pair in song_artist_pairs]

    openai_songs_spotify_details = []
    for song, artist in song_artist_pairs:
        song_details = get_song_details_from_spotify(song, artist)
        if song_details:
            openai_songs_spotify_details.append(song_details)

    # Get Spotify track IDs using the song titles and artists
    track_ids = get_spotify_track_ids(song_titles, suggested_artists, access_token)

    # Extract artist IDs from the songs recommended by OpenAI
    artist_ids = get_artist_ids_from_names(artists, access_token)

    # Now, pass artist_ids and track_ids as seed_artists and seed_tracks to the function
    audio_features = get_audio_features(track_ids, access_token)
    matching_songs = get_recommendations_based_on_features(audio_features, artist_ids, track_ids, access_token,
                                                           song_count)
    if gender_preference is not None:
        matching_songs = ask_openai_to_classify_gender_and_filter_songs(matching_songs, gender_preference)

    combined_songs = merge_songs(openai_songs_spotify_details, matching_songs)

    return jsonify({"songs": combined_songs})


@spotify_blueprint.route('/search-artists')
def search_artists_endpoint():
    query = request.args.get('query')
    if not query:
        return jsonify({"error": "Query parameter is required"}), 400
    access_token = session.get('access_token')
    artists = search_artists(query, access_token)
    if artists:
        return jsonify({"artists": artists})
    else:
        return jsonify({"error": "Failed to fetch artists or no artists found"}), 404


@spotify_blueprint.route('/available-genres', methods=['GET'])
def available_genres():
    access_token = session.get('access_token')
    genres = get_available_genres_from_spotify(access_token)
    return jsonify(genres)
