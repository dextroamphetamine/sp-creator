import os
import re

import openai

from .musicbrainz import get_artist_info

openai.api_key = os.environ.get('OPENAI_KEY')


def ask_openai_for_songs(moods, activities, artists, song_count, genres=None, gender_preference=None):
    prompt = (f"I'm looking for song recommendations. Given the mood(s) {', '.join(moods)}, "
              f"for an activity like {activities}, and preferences for artists such as {', '.join(artists)}")

    if genres:
        prompt += f", preferably from the {', '.join(genres)} genre."

    if gender_preference:
        prompt += f" I would also like you to include artists that are only of the {gender_preference} gender. "

    prompt += (
        f" Please suggest specific songs in exactly this format: '\"Song Title\" by \"Artist\"'. I want exactly {song_count} number of songs.")

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": prompt
        }],
        max_tokens=1000
    )

    return response.choices[0].message.content.strip()


def ask_openai_to_classify_gender_and_filter_songs(artists: [dict], gender_preference: str):
    artists_to_query: [dict] = []
    artist_id_set: set = set()
    artist_name_list: [str] = []
    for artist in artists:
        if artist['artists']:
            for album_artist in artist['artists']:
                if album_artist['id'] not in artist_id_set:
                    artist_id_set.add(album_artist['id'])
                    artists_to_query.append(album_artist)
                    artist_name_list.append(album_artist['name'])

    artist_info = get_artist_info(artist_name_list)

    filtered_artists_by_gender: [dict] = []
    for query_artist in artists_to_query:
        found_artist: dict = {}
        for a in artist_info['artists']:
            if a['name'] == query_artist['name']:
                if 'gender' in a and a['gender'] == gender_preference:
                    filtered_artists_by_gender.append(query_artist)
                    break
    artist_id_list = [entry['id'] for entry in filtered_artists_by_gender]
    return [
        artist for artist in artists
        if artist['artists'][0]['id'] in artist_id_list
    ]


def parse_openai_response(response):
    # Regular expression pattern to match song titles and artists
    pattern = r'\"(.*?)\" by (.*?)\n'
    matches = re.findall(pattern, response)

    # Convert matches to a list of tuples
    song_artist_pairs = [(match[0], match[1]) for match in matches]

    return song_artist_pairs
