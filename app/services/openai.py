import openai
import os
import re
import requests
from textblob import TextBlob
openai.api_key = os.environ.get('OPENAI_KEY')

def ask_openai_for_songs(moods, activities, artists, song_count):
    prompt = (f"I'm looking for song recommendations. Given the mood(s) {', '.join(moods)}, "
              f"for an activity like {activities}, and preferences for artists such as {', '.join(list(map(lambda artist: artist['name'], artists)))}"
              f"please suggest specific songs in the format 'Song Title by Artist' I want exactly {song_count} number of songs.")
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{
          "role": "user",
          "content": prompt
        }],
        max_tokens=500
    )
    
    return response.choices[0].message.content.strip()

def parse_openai_response(response):
    # Regular expression pattern to match song titles and artists
    pattern = r'\"(.*?)\" by (.*?)\n'
    matches = re.findall(pattern, response)
    
    # Convert matches to a list of tuples
    song_artist_pairs = [(match[0], match[1]) for match in matches]
    
    return song_artist_pairs

