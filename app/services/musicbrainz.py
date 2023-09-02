import requests
from typing import Dict, Optional, Callable

BASE_MUSICBRAINZ_URL = "https://musicbrainz.org/ws/2/"

def make_musicbrainz_request(endpoint: str, headers: Dict[str, str], method: str = "GET", params: Optional[Dict] = None, json: Optional[Dict] = None, retries: int = 1) -> Dict:
    url = BASE_MUSICBRAINZ_URL + endpoint
    response = requests.request(method, url, headers=headers, params=params, json=json)
    
    response.raise_for_status()
    return response.json()