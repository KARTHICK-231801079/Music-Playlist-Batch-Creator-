import sys
import os
import shutil
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from PyQt6.QtWidgets import QApplication, QFileDialog

def create_directory(path):
    """Create a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def extract_metadata(file_path):
    """Extracts genre and artist metadata from an MP3 file."""
    try:
        audio = EasyID3(file_path)
        genre = audio.get('genre', ['Unknown'])[0]
        artist = audio.get('artist', ['Unknown'])[0]
    except Exception:
        try:
            audio = MP3(file_path)
            tags = audio.tags
            if tags:
                genre = tags.get('TCON', ["Unknown"])[0]
                artist = tags.get('TPE1', ["Unknown"])[0]
            else:
                print(f"Warning: No ID3 tags found for {file_path}")
                return "Unknown", "Unknown"
        except Exception as e:
            print(f"Error reading metadata for {file_path}: {e}")
            return "Unknown", "Unknown"
    
    print(f"Extracted Metadata - Artist: {artist}, Genre: {genre}")
    return genre, artist

def process_file(file_path):
    """Sorts the file into output/Genre/Artist/ and copies it there."""
    genre, artist = extract_metadata(file_path)
    
    output_folder = os.path.join("output", genre, artist)
    create_directory(output_folder)
    
    shutil.copy(file_path, output_folder)
    print(f"Uploaded: {os.path.basename(file_path)} → {output_folder}")

def process_folder(folder_path):
    """Processes all MP3 files inside a folder."""
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.mp3'):
                file_path = os.path.join(root, file)
                process_file(file_path)

def upload_mp3():
    """Opens a file dialog for selecting MP3 files or a folder."""
    app = QApplication(sys.argv)
    
    folder = QFileDialog.getExistingDirectory(None, "Select Folder Containing MP3s")
    
    if folder:
        process_folder(folder)
    else:
        print("No folder selected. Please select a folder containing MP3 files.")

if __name__ == "__main__":
    upload_mp3()
