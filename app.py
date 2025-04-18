from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import pickle
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import difflib

app = Flask(__name__)

# Load recommendation model files
with open('music_df.pkl', 'rb') as file:
    music_df = pickle.load(file)
with open('lyrics_similarity_mapping.pkl', 'rb') as file:
    cosine_lyrics = pickle.load(file)
with open('mood_similarity_mapping.pkl', 'rb') as file:
    cosine_mood = pickle.load(file)
with open('genre_similarity_mapping.pkl', 'rb') as file:
    cosine_genre = pickle.load(file)

# Set up Spotify API credentials (replace with your credentials)
SPOTIPY_CLIENT_ID = 'Enter Spotify Client Id'
SPOTIPY_CLIENT_SECRET = 'Enter Spotify Client Secret'
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                           client_secret=SPOTIPY_CLIENT_SECRET))

# Define mood categories for filtering
MOOD_CATEGORIES = {
    "happy": lambda x: x['valence'] > 0.6 and x['energy'] > 0.6,
    "sad": lambda x: x['valence'] < 0.4 and x['energy'] < 0.5,
    "love": lambda x: x['valence'] > 0.5 and x['acousticness'] > 0.4,
    "workout": lambda x: x['energy'] > 0.7 and x['tempo'] > 120,
    "instrumental": lambda x: x['instrumentalness'] > 0.5
}

def get_similar_indices(song_index, top_n, similarity_matrix, include_self=True):
    """Return the indices of the top-N most similar songs."""
    similar_indices = np.argsort(similarity_matrix[song_index])[::-1]
    if not include_self:
        similar_indices = similar_indices[similar_indices != song_index]
    return similar_indices[:top_n]

def recommend_by_artist(artist_name, top_n=10):
    """Recommend songs by a given artist."""
    artist_songs = music_df[music_df["track_artist"].str.lower() == artist_name.lower()]
    if artist_songs.empty:
        return None
    return artist_songs.sample(n=min(top_n, len(artist_songs)))

def recommend_by_lyrics(song_name, top_n=10):
    """Recommend songs based on lyrics similarity."""
    matched_songs = music_df[music_df["track_name"].str.lower() == song_name.lower()]
    if matched_songs.empty:
        return None
    song_index = matched_songs.index[0]
    similar_indices = get_similar_indices(song_index, top_n, cosine_lyrics)
    return music_df.iloc[similar_indices]

def recommend_by_mood(mood, top_n=10):
    """Recommend songs based on mood."""
    if mood not in MOOD_CATEGORIES:
        return None
    filtered_songs = music_df[music_df.apply(lambda row: MOOD_CATEGORIES[mood](row), axis=1)]
    if not filtered_songs.empty:
        return filtered_songs.sample(n=min(top_n, len(filtered_songs)))
    # Fallback using mood similarity if direct filtering yields nothing
    if mood in cosine_mood:
        mood_sim_matrix = cosine_mood[mood]
        similar_indices = np.argsort(mood_sim_matrix)[::-1][:top_n]
        return music_df.iloc[similar_indices]
    return None

def recommend_by_genre(genre, top_n=10):
    """Recommend songs based on genre."""
    genre = genre.strip().lower()
    filtered_songs = music_df[(music_df["playlist_genre"].str.lower() == genre) |
                              (music_df["playlist_subgenre"].str.lower() == genre)]
    if not filtered_songs.empty:
        return filtered_songs.sample(n=min(top_n, len(filtered_songs)))
    if genre in cosine_genre:
        genre_sim_matrix = cosine_genre[genre]
        similar_indices = np.argsort(genre_sim_matrix)[::-1][:top_n]
        return music_df.iloc[similar_indices]
    return None

def generate_playlist(user_choice, song_name=None, mood=None, genre=None, artist_name=None, top_n=10):
    """Generate a playlist based on the recommendation type.
       Options:
         "1" - Popularity
         "2" - Artist
         "3" - Random
         "4" - Lyrics
         "5" - Mood
         "6" - Genre
    """
    if user_choice == "1":  # Popularity
        return music_df.sort_values(by="track_popularity", ascending=False).head(top_n)
    elif user_choice == "2":  # Artist
        if not artist_name:
            return None
        return recommend_by_artist(artist_name, top_n)
    elif user_choice == "3":  # Random
        return music_df.sample(n=top_n)
    elif user_choice == "4":  # Lyrics
        if not song_name:
            return None
        return recommend_by_lyrics(song_name, top_n)
    elif user_choice == "5":  # Mood
        if not mood:
            return None
        return recommend_by_mood(mood, top_n)
    elif user_choice == "6":  # Genre
        if not genre:
            return None
        return recommend_by_genre(genre, top_n)
    else:
        return None

def get_spotify_track_details(track_name, artist_name):
    """Fetch track details from Spotify API."""
    query = f"track:{track_name} artist:{artist_name}"
    results = sp.search(q=query, type="track", limit=1)
    if results and results["tracks"]["items"]:
        track = results["tracks"]["items"][0]
        return {
            "track_name": track['name'],
            "track_artist": track['artists'][0]['name'],
            "album_name": track['album']['name'],
            "release_date": track['album']['release_date'],
            "album_image": track['album']['images'][0]['url'] if track['album']['images'] else "static/default_album.jpg",
            "preview_url": track['preview_url'],
            "spotify_url": track['external_urls']['spotify']
        }
    # Fallback if no details are found
    return {
        "track_name": track_name,
        "track_artist": artist_name,
        "album_name": "Not available",
        "release_date": "Not available",
        "album_image": "static/default_album.jpg",
        "preview_url": None,
        "spotify_url": "#"
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    playlist = None
    message = ""
    if request.method == "POST":
        user_choice = request.form.get("user_choice")
        song_name = request.form.get("song_name")
        mood = request.form.get("mood")
        genre = request.form.get("genre")
        artist_name = request.form.get("artist_name")
        
        playlist_df = generate_playlist(user_choice, song_name, mood, genre, artist_name)
        if playlist_df is None or playlist_df.empty:
            message = "❌ No songs found. Please try again."
        else:
            # Enrich each song with metadata from Spotify
            playlist = []
            for _, row in playlist_df.iterrows():
                details = get_spotify_track_details(row['track_name'], row['track_artist'])
                playlist.append(details)
    return render_template("index.html", playlist=playlist, message=message)

@app.route('/suggest', methods=['GET'])
def suggest():
    """Provide song title suggestions based on partial user input."""
    query = request.args.get('query', '').strip().lower()
    if not query:
        return jsonify([])
    # We assume the music DataFrame has a column 'track_name'
    song_titles = music_df['track_name'].str.lower().tolist()
    suggestions = difflib.get_close_matches(query, song_titles, n=5, cutoff=0.5)
    return jsonify(suggestions)

@app.route('/trending', methods=['GET'])
def trending():
    """Return trending songs based on popularity."""
    trending_df = music_df.sort_values(by="track_popularity", ascending=False).head(10)
    trending_list = []
    for _, row in trending_df.iterrows():
        details = get_spotify_track_details(row['track_name'], row['track_artist'])
        trending_list.append(details)
    return jsonify(trending_list)

if __name__ == "__main__":
    app.run(debug=True)
