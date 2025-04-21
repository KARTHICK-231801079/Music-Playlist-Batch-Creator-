import pandas as pd
import pickle

# Load the dataset
def load_pickle(file_path):
    with open(file_path, 'rb') as file:
        return pickle.load(file)

music_df = load_pickle('music_df.pkl')

# Load the trained DBSCAN model
dbscan_model = load_pickle('dbscan_model.pkl')


music_df['cluster'] = dbscan_model.labels_

# Function to recommend songs based on DBSCAN clusters
def recommend_by_cluster(song_name, top_n=10):
    matched_song = music_df[music_df["track_name"].str.lower() == song_name.lower()]
    
    if matched_song.empty:
        return f"❌ No matching song found for '{song_name}'. Please try another song."
    
    song_cluster = matched_song['cluster'].values[0]
    
    if song_cluster == -1:
        return f"⚠️ The song '{song_name}' is classified as noise (outlier) and has no cluster."
    
    # Get songs from the same cluster
    cluster_songs = music_df[music_df['cluster'] == song_cluster]
    
    if cluster_songs.empty or len(cluster_songs) <= 1:
        return f"❌ No recommendations found for cluster {song_cluster}."
    
    return cluster_songs.sample(n=min(top_n, len(cluster_songs)))

# Take user input
song_name = input("Enter a song name: ").strip()

recommendations = recommend_by_cluster(song_name)


if isinstance(recommendations, str):
    print(recommendations)
else:
    print("\n🎵 **Recommended Songs:**")
    for _, song in recommendations.iterrows():
        print(f"🎶 {song['track_name']} by {song['track_artist']} ({song['playlist_genre']})")
