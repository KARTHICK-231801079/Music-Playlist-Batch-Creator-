from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import pandas as pd
import numpy as np
import pickle
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import difflib
from pymongo import MongoClient
import pymongo
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Secret key for session management
app.secret_key = 'your_secret_key'

# MongoDB URL (ensure this is correct)
MONGODB_URL = "Enter your MongoDB URL"  # Replace with your MongoDB URL
DATABASE_NAME = 'Music'
COLLECTION_NAME = 'User_Details'

# Connecting to MongoDB with error handling
try:
    client = pymongo.MongoClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    users_collection = db[COLLECTION_NAME]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")
    exit()

# Load recommendation model files with error handling
try:
    with open('music_df.pkl', 'rb') as file:
        music_df = pickle.load(file)
    with open('lyrics_similarity_mapping.pkl', 'rb') as file:
        cosine_lyrics = pickle.load(file)
    with open('mood_similarity_mapping.pkl', 'rb') as file:
        cosine_mood = pickle.load(file)
    with open('genre_similarity_mapping.pkl', 'rb') as file:
        cosine_genre = pickle.load(file)
except Exception as e:
    print(f"Error loading model files: {e}")
    exit()

# Set up Spotify API credentials (replace with your credentials)
SPOTIPY_CLIENT_ID = '03b084fb5cd243b996cdf71a28478a2c'
SPOTIPY_CLIENT_SECRET = 'f29f318f211944cc8bb218272a6292f0'
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
    """Generate a playlist based on the recommendation type."""
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
    return {
        "track_name": track_name,
        "track_artist": artist_name,
        "album_name": "Not available",
        "release_date": "Not available",
        "album_image": "static/default_album.jpg",
        "preview_url": None,
        "spotify_url": "#"
    }

# Route for index page
@app.route("/", methods=["GET", "POST"])
def index():
    playlist = None
    message = ""
    if "username" in session:
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
    else:
        return redirect(url_for("login"))

# Route for login page
@app.route("/login", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        # Check if user exists
        user = users_collection.find_one({"username": username})
        if user and check_password_hash(user["password"], password):
            session["username"] = username  # Store username in session
            return redirect(url_for("index"))
        else:
            message = "❌ Invalid credentials. Please try again."
    return render_template("login.html", message=message)

# Route for register page
@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        age = request.form.get("age")
        dob = request.form.get("dob")

        # Validate all fields are filled
        if not all([first_name, last_name, username, email, password, age, dob]):
            message = "❌ All fields are required."
        # Check if username already exists
        elif users_collection.find_one({"username": username}):
            message = "❌ Username already exists."
        # Check if email already exists
        elif users_collection.find_one({"email": email}):
            message = "❌ Email already registered."
        else:
            hashed_password = generate_password_hash(password)
            # Insert user data into database
            users_collection.insert_one({
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "email": email,
                "password": hashed_password,
                "age": int(age),
                "dob": dob
            })
            message = "✅ Registration successful. Please login."
            return redirect(url_for("login"))

    return render_template("register.html", message=message)

# Route to logout
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
