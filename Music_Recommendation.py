import pandas as pd
import numpy as np
import pickle
import random

# Load pickle files
def load_pickle(file_path):
    with open(file_path, 'rb') as file:
        return pickle.load(file)

# Load data
music_df = load_pickle('music_df.pkl')
cosine_lyrics = load_pickle('lyrics_similarity_mapping.pkl')
cosine_mood = load_pickle('mood_similarity_mapping.pkl')
cosine_genre = load_pickle('genre_similarity_mapping.pkl')

# Define Mood Mapping
MOOD_CATEGORIES = {
    "happy": lambda x: x['valence'] > 0.6 and x['energy'] > 0.6,
    "sad": lambda x: x['valence'] < 0.4 and x['energy'] < 0.5,
    "love": lambda x: x['valence'] > 0.5 and x['acousticness'] > 0.4,
    "workout": lambda x: x['energy'] > 0.7 and x['tempo'] > 120,
    "instrumental": lambda x: x['instrumentalness'] > 0.5
}

# Function to get top-N most similar songs
def get_similar_indices(song_index, top_n, similarity_matrix, include_self=True):
    """Returns the top-N most similar song indices based on the similarity matrix."""
    similar_indices = np.argsort(similarity_matrix[song_index])[::-1]
    if not include_self:
        similar_indices = similar_indices[similar_indices != song_index]
    return similar_indices[:top_n]

# Function to recommend songs by artist
def recommend_by_artist(artist_name, top_n=10):
    """Returns songs by a specific artist."""
    artist_songs = music_df[music_df["track_artist"].str.lower() == artist_name.lower()]
    
    if artist_songs.empty:
        return f"❌ No songs found for artist '{artist_name}'. Please try another artist."
    
    return artist_songs.sample(n=min(top_n, len(artist_songs)))

# Function to recommend songs by lyrics similarity
def recommend_by_lyrics(song_name, top_n=10):
    """Returns songs similar to a given song based on lyrics."""
    matched_songs = music_df[music_df["track_name"].str.lower() == song_name.lower()]
    
    if matched_songs.empty:
        return f"❌ No matching song found for '{song_name}'. Please try another song."

    song_index = matched_songs.index[0]
    similar_songs = get_similar_indices(song_index, top_n, cosine_lyrics)
    return music_df.iloc[similar_songs]

def recommend_by_mood(mood, top_n=10):
    """Returns songs matching a specific mood using both direct filtering and mood similarity matrix."""
    if mood not in MOOD_CATEGORIES:
        return f"❌ Invalid mood selection. Choose from: {', '.join(MOOD_CATEGORIES.keys())}"

    # Step 1: Direct Filtering (First Priority)
    filtered_songs = music_df[music_df.apply(lambda row: MOOD_CATEGORIES[mood](row), axis=1)]
    if not filtered_songs.empty:
        return filtered_songs.sample(n=min(top_n, len(filtered_songs)))

    # Step 2: Use Mood Similarity Matrix (Fallback)
    if mood in cosine_mood:
        mood_sim_matrix = cosine_mood[mood]  # Get similarity scores for the given mood
        similar_song_indices = np.argsort(mood_sim_matrix)[::-1][:top_n]  # Get top-N similar songs
        return music_df.iloc[similar_song_indices]

    return f"❌ No songs found for mood '{mood}'."

# Function to recommend by genre using cosine similarity
def recommend_by_genre(genre, top_n=10):
    """Returns songs matching a specific genre using similarity metrics."""
    genre = genre.strip().lower()
    filtered_songs = music_df[
        (music_df["playlist_genre"].str.lower() == genre) | 
        (music_df["playlist_subgenre"].str.lower() == genre)
    ]

    if not filtered_songs.empty:
        return filtered_songs.sample(n=min(top_n, len(filtered_songs)))
    
    if genre in cosine_genre:
        genre_sim_matrix = cosine_genre[genre]
        similar_songs_indices = np.argsort(genre_sim_matrix)[::-1][:top_n]
        return music_df.iloc[similar_songs_indices]
    
    return f"❌ No songs found for genre '{genre}'."

# Function to generate a playlist
def generate_playlist(user_choice, song_name=None, mood=None, genre=None, artist_name=None, top_n=10):
    """Generates a playlist based on the user’s preference."""
    if user_choice == 1:  # Popularity
        return music_df.sort_values(by="track_popularity", ascending=False).head(top_n)
    
    elif user_choice == 2:  # Artist
        if artist_name is None:
            artist_name = input("Enter the artist name: ").strip()
        return recommend_by_artist(artist_name, top_n)
    
    elif user_choice == 3:  # Random
        return music_df.sample(n=top_n)
    
    elif user_choice == 4:  # Lyrics
        if song_name is None:
            song_name = input("Enter a song name to find similar lyrics: ").strip()
        return recommend_by_lyrics(song_name, top_n)
    
    elif user_choice == 5:  # Mood
        if mood is None:
            mood = input(f"Choose mood ({', '.join(MOOD_CATEGORIES.keys())}): ").strip()
        return recommend_by_mood(mood, top_n)
    
    elif user_choice == 6:  # Genre
        if genre is None:
            genre = input("Enter genre: ").strip()
        return recommend_by_genre(genre, top_n)
    
    elif user_choice == 7:  # Combination
        top_popular = music_df.sort_values(by="track_popularity", ascending=False).head(top_n // 3)
        random_songs = music_df.sample(n=top_n // 3)
        top_lyrical = music_df.iloc[get_similar_indices(random.randint(0, len(music_df)-1), top_n // 3, cosine_lyrics)]
        return pd.concat([top_popular, random_songs, top_lyrical])
    
    return "❌ Invalid choice or missing input."

# Playlist Naming System
playlist_name_map = {
    1: "🔥 Chart-Toppers Mix – The Ultimate Hits!",
    2: "🎤 Artist Essentials – Fan Favorites!",
    3: "🎲 Shuffle Mode: Your Surprise Jams!",
    4: "🎶 Lyrically Yours – Songs That Feel Like Poetry",
    5: "🎭 Mood Vibes – Music That Matches Your Mood!",
    6: "🎸 Genre Gems – Handpicked Just for You!",
    7: "🌟 Your Ultimate Playlist – A Perfect Blend!"
}

# Ask user for input
print("\n🎵 **Welcome to the Music Recommendation System!** 🎵")
print("Choose recommendation type:")
print("1: Popularity")
print("2: Artist")
print("3: Random")
print("4: Lyrics")
print("5: Mood")
print("6: Genre")
print("7: Combination")

user_choice = int(input("Enter your choice (1-7): "))

# Get additional inputs if needed
song_name, mood, genre, artist_name = None, None, None, None
if user_choice == 2:
    artist_name = input("Enter the artist name: ")
elif user_choice == 4:
    song_name = input("Enter a song name to find similar lyrics: ")
elif user_choice == 5:
    mood = input(f"Choose mood ({', '.join(MOOD_CATEGORIES.keys())}): ")
elif user_choice == 6:
    genre = input("Enter genre: ")

# Generate and display the playlist
playlist = generate_playlist(user_choice, song_name, mood, genre, artist_name)
playlist_name = playlist_name_map.get(user_choice, "🎵 Your Custom Playlist")

if isinstance(playlist, str):  # Handle error messages
    print(playlist)
else:
    print(f"\n🎵 **Playlist Name:** {playlist_name}")
    for _, song in playlist.iterrows():
        print(f"🎶 {song['track_name']} by {song['track_artist']} ({song['playlist_genre']})")
