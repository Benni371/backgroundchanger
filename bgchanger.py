#!/usr/bin/env python3
"""
Windows Desktop Background Changer using Pexels API
Usage: python bgchanger.py <query_term> [local_only]
"""

import os
import sys
import json
import hashlib
import requests
import random
from pathlib import Path
import ctypes
from ctypes import wintypes
from dotenv import load_dotenv
load_dotenv()

# Constants
PEXELS_API_URL = "https://api.pexels.com/v1/search"
WALLPAPERS_DIR = Path("wallpapers")
HASH_FILE = "image_hashes.json"
DEFAULT_API_KEY = os.getenv("pexels_api_key")  # Replace with your actual API key

# Windows API constants
SPI_SETDESKWALLPAPER = 20
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDWININICHANGE = 0x02

class BackgroundChanger:
    def __init__(self, api_key=None):
        self.api_key = api_key or DEFAULT_API_KEY
        self.base_dir = WALLPAPERS_DIR
        self.hash_file_path = self.base_dir / HASH_FILE
        self.used_hashes = self.load_used_hashes()
        
        # Create base wallpapers directory if it doesn't exist
        self.base_dir.mkdir(exist_ok=True)
    
    def load_used_hashes(self):
        """Load previously used image hashes from file"""
        if self.hash_file_path.exists():
            try:
                with open(self.hash_file_path, 'r') as f:
                    return set(json.load(f))
            except (json.JSONDecodeError, IOError):
                return set()
        return set()
    
    def save_used_hashes(self):
        """Save used image hashes to file"""
        try:
            with open(self.hash_file_path, 'w') as f:
                json.dump(list(self.used_hashes), f)
        except IOError as e:
            print(f"Warning: Could not save hash file: {e}")
    
    def get_image_hash(self, image_data):
        """Calculate SHA-256 hash of image data"""
        return hashlib.sha256(image_data).hexdigest()
    
    def set_wallpaper(self, image_path):
        """Set Windows desktop wallpaper using ctypes"""
        try:
            # Convert path to absolute path
            abs_path = os.path.abspath(image_path)
            
            # Call Windows API to set wallpaper
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                abs_path,
                SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE
            )
            
            if result:
                print(f"Successfully set wallpaper: {abs_path}")
                return True
            else:
                print("Failed to set wallpaper")
                return False
                
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            return False
    
    def download_image(self, url, save_path):
        """Download image from URL and save to specified path"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # Get image data
            image_data = response.content
            
            # Check if we've used this image before
            image_hash = self.get_image_hash(image_data)
            if image_hash in self.used_hashes:
                print("Image already used, skipping...")
                return None
            
            # Save image
            with open(save_path, 'wb') as f:
                f.write(image_data)
            
            # Add hash to used set
            self.used_hashes.add(image_hash)
            self.save_used_hashes()
            
            print(f"Downloaded image: {save_path}")
            return save_path
            
        except requests.RequestException as e:
            print(f"Error downloading image: {e}")
            return None
        except IOError as e:
            print(f"Error saving image: {e}")
            return None
    
    def fetch_from_pexels(self, query_term):
        """Fetch a random image from Pexels API"""
        
        try:
            headers = {"Authorization": self.api_key}
            params = {
                "query": query_term,
                "per_page": 80,  # Get more images to have variety
                "page": random.randint(1, 10)  # Random page for more variety
            }
            
            response = requests.get(PEXELS_API_URL, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            photos = data.get("photos", [])
            
            if not photos:
                print(f"No images found for query: {query_term}")
                print(f"Quering local folders for query: {query_term}")
                self.get_local_image(query_term)
                return None
            
            # Try multiple images until we find one we haven't used
            random.shuffle(photos)
            for photo in photos:
                image_url = photo["src"]["original"]
                
                # Create filename from photo ID
                filename = f"pexels_{photo['id']}.jpg"
                query_dir = self.base_dir / query_term
                query_dir.mkdir(exist_ok=True)
                save_path = query_dir / filename
                
                # Skip if file already exists
                if save_path.exists():
                    continue
                
                # Try to download
                downloaded_path = self.download_image(image_url, save_path)
                if downloaded_path:
                    return downloaded_path
            
            print("All available images have been used")
            return None
            
        except requests.RequestException as e:
            print(f"Error fetching from Pexels API: {e}")
            return None
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Error parsing API response: {e}")
            return None
    
    def get_local_image(self, query_term):
        """Get a random unused local image from the query term folder"""
        query_dir = self.base_dir / query_term
        
        if not query_dir.exists():
            print(f"Local folder not found: {query_dir}")
            return None
        
        # Get all image files
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
        image_files = [
            f for f in query_dir.iterdir() 
            if f.is_file() and f.suffix.lower() in image_extensions
        ]
        
        if not image_files:
            print(f"No image files found in: {query_dir}")
            return None
        
        # Select random unused image
        selected_image = random.choice(image_files)
        
        return selected_image
    
    def change_background(self, query_term, local_only=False):
        """Main method to change desktop background"""
        if local_only:
            print(f"Using local images only for query: {query_term}")
            image_path = self.get_local_image(query_term)
        else:
            print(f"Fetching new image for query: {query_term}")
            image_path = self.fetch_from_pexels(query_term)
        
        if image_path:
            success = self.set_wallpaper(image_path)
            if success:
                print(f"Desktop background changed successfully!")
            return success
        else:
            print("Could not get a new image")
            return False

def main():
    if len(sys.argv) < 1:
        print("Usage: python bgchanger.py [local_only]")
        print("Example: python bgchanger.py true")
        sys.exit(1)
    term_list = ["mountains", "polygon", "abstract", "4k wallpaper", "landscape"]
    query_term = random.choice(term_list)
    local_only = False
    
    if len(sys.argv) > 2:
        local_only_arg = sys.argv[1].lower()
        local_only = local_only_arg in ['true', '1', 'yes', 'on']
    
    # Initialize the background changer
    bg_changer = BackgroundChanger()
    
    # Change the background
    success = bg_changer.change_background(query_term, local_only)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()