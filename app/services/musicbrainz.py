from typing import Dict, Optional

import requests

BASE_MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/"


def _make_musicbrainz_request(endpoint: str, headers: Dict[str, str], method: str = "GET",
                              params: Optional[Dict] = None, json: Optional[Dict] = None, retries: int = 1) -> Dict:
    url = BASE_MUSICBRAINZ_URL + endpoint
    response = requests.request(method, url, headers=headers, params=params, json=json)

    response.raise_for_status()
    return response.json()


def _get_artist_info_by_names(artists: [str]):
    url = "artist/"
    params = _format_artists_querey(artists)
    headers = {
        "Accept": "application/json"
    }
    return _make_musicbrainz_request(url, headers, method='GET', params=params)


def _format_artists_querey(artists: [str]):
    query_params = "artist:"
    for index, artist in enumerate(artists):
        query_params += artist
        if index < len(artists):
            query_params += ", "

    return {
        'query': query_params
    }


def get_artist_info(artists: [str]):
    artist_info = _get_artist_info_by_names(artists)

    return artist_info
