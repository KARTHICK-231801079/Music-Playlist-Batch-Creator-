import requests
import pandas as pd
import time
from tqdm import tqdm
import random

# Spotify API credentials (replace with your own)
CLIENT_ID = "835d9da007be4017aebb3f09eac4036b"
CLIENT_SECRET = "ed04f67ec93e44b98fa2ab797c420d7c"

# Authenticate and get access token
def get_access_token():
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials", "client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
    response = requests.post(url, headers=headers, data=data)
    return response.json().get("access_token")

ACCESS_TOKEN = get_access_token()
HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# Get track details
def get_track_details(track):
    track_info = track.get("track", {})
    if not track_info:
        return None
    release_year = track_info.get("album", {}).get("release_date", "Unknown").split("-")[0]
    if release_year == "Unknown" or int(release_year) < 2005:
        return None
    return {
        "artist_name": track_info.get("artists", [{}])[0].get("name", "Unknown"),
        "song_name": track_info.get("name", "Unknown"),
        "track_id": track_info.get("id", "Unknown"),
        "release_year": release_year,
        "playlist_name": track.get("playlist_name", "Unknown")
    }

# Get track features
def get_audio_features(track_id):
    url = f"https://api.spotify.com/v1/audio-features/{track_id}"
    response = requests.get(url, headers=HEADERS).json()
    if not response or "error" in response:
        return {}
    return {
        "tempo": response.get("tempo"),
        "energy": response.get("energy"),
        "valence": response.get("valence"),
        "loudness": response.get("loudness"),
        "danceability": response.get("danceability"),
        "speechiness": response.get("speechiness"),
        "instrumentalness": response.get("instrumentalness")
    }

# Define years and number of songs per year
years = list(range(2005, 2026))  # Start from 2005
num_songs_per_year = {year: random.randint(10, 50) for year in years}  # Ensure max limit is 50

data = []
for year in tqdm(years):
    search_url = f"https://api.spotify.com/v1/search?q=year:{year}&type=track&limit={num_songs_per_year[year]}"
    response = requests.get(search_url, headers=HEADERS).json()
    if "error" in response:
        print(f"Error fetching data for year {year}: {response['error']}")
        continue
    tracks = response.get("tracks", {}).get("items", [])
    print(f"Year {year}: Found {len(tracks)} tracks")
    
    for track in tracks:
        track_details = get_track_details({"track": track})
        if track_details:
            track_features = get_audio_features(track_details["track_id"])
            track_details.update(track_features)
            track_details["playlist_name"] = track.get("album", {}).get("name", "Unknown")
            data.append(track_details)

if data:
    df = pd.DataFrame(data)
    df.to_csv("spotify_music_dataset_25.csv", index=False)
    print("Dataset saved successfully!")
else:
    print("No data collected. Check API responses.")
