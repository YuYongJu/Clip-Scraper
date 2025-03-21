#!/usr/bin/env python3
import os
import re
import argparse
import json
from pathlib import Path
import random
import time
from urllib.parse import urlparse, urljoin

import requests
from bs4 import BeautifulSoup
import yt_dlp

class AnimeClipScraper:
    def __init__(self, output_dir="downloads", config_file="config.json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = config_file
        self.load_config()
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
    def load_config(self):
        """Load configuration from JSON file or create default"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            # Default configuration
            self.config = {
                "sources": [
                    {
                        "name": "sakugabooru",
                        "base_url": "https://www.sakugabooru.com/post?tags=animated",
                        "page_param": "page={}",
                        "clip_selector": "article.post-preview",
                        "link_selector": "a.directlink",
                        "next_page_selector": "a.next_page",
                        "max_pages": 3
                    },
                    {
                        "name": "animeclips_reddit",
                        "base_url": "https://www.reddit.com/r/animegifs/hot/.json",
                        "is_api": True,
                        "max_items": 20
                    }
                ],
                "download_limit": 10,
                "min_delay": 1,
                "max_delay": 3,
                "categories": ["action", "fight", "emotional", "comedy"]
            }
            self.save_config()
    
    def save_config(self):
        """Save current configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def random_delay(self):
        """Add random delay between requests to avoid rate limiting"""
        delay = random.uniform(self.config["min_delay"], self.config["max_delay"])
        time.sleep(delay)
    
    def scrape_sakugabooru(self, source):
        """Scrape anime clips from Sakugabooru"""
        clips = []
        current_page = 1
        
        while current_page <= source["max_pages"]:
            url = source["base_url"]
            if current_page > 1:
                url = f"{url}&{source['page_param'].format(current_page)}"
            
            print(f"Scraping {source['name']} page {current_page}...")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Failed to fetch {url}, status code: {response.status_code}")
                break
            
            soup = BeautifulSoup(response.text, 'html.parser')
            clip_elements = soup.select(source["clip_selector"])
            
            for element in clip_elements:
                try:
                    # Extract video link
                    link_element = element.select_one(source["link_selector"])
                    if not link_element:
                        continue
                    
                    link = link_element.get('href')
                    if not link:
                        continue
                    
                    # Only get video files
                    if any(ext in link.lower() for ext in ['.mp4', '.webm', '.gif']):
                        # Make URL absolute if needed
                        if not urlparse(link).netloc:
                            link = urljoin(source["base_url"], link)
                        
                        # Get tags if available
                        tags = []
                        tags_element = element.get('data-tags')
                        if tags_element:
                            tags = tags_element.split()
                        
                        clips.append({
                            "source": source["name"],
                            "url": link,
                            "tags": tags
                        })
                except Exception as e:
                    print(f"Error processing clip element: {str(e)}")
            
            # Check if we've reached the limit
            if len(clips) >= self.config["download_limit"]:
                break
            
            # Find next page link
            next_page = soup.select_one(source["next_page_selector"])
            if not next_page:
                break
            
            current_page += 1
            self.random_delay()
        
        return clips[:self.config["download_limit"]]
    
    def scrape_reddit(self, source):
        """Scrape anime clips from Reddit"""
        clips = []
        
        # Reddit requires a JSON request
        headers = self.headers.copy()
        headers["Accept"] = "application/json"
        
        response = requests.get(source["base_url"], headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch {source['base_url']}, status code: {response.status_code}")
            return clips
        
        data = response.json()
        posts = data.get("data", {}).get("children", [])
        
        for post in posts[:source["max_items"]]:
            post_data = post.get("data", {})
            url = post_data.get("url")
            
            # Skip if not a direct media link or if it's a gallery
            if not url or "gallery" in url or "v.redd.it" not in url and not url.endswith(('.mp4', '.gif', '.webm')):
                continue
            
            # For v.redd.it links, get the actual media URL
            if "v.redd.it" in url:
                fallback_url = post_data.get("secure_media", {}).get("reddit_video", {}).get("fallback_url")
                if fallback_url:
                    url = fallback_url
            
            clips.append({
                "source": source["name"],
                "url": url,
                "title": post_data.get("title", ""),
                "author": post_data.get("author", ""),
                "tags": []
            })
            
            if len(clips) >= self.config["download_limit"]:
                break
        
        return clips
    
    def download_clips(self, clips, category=None):
        """Download clips to the output directory"""
        download_dir = self.output_dir
        if category:
            download_dir = self.output_dir / category
            download_dir.mkdir(exist_ok=True)
        
        for i, clip in enumerate(clips):
            try:
                url = clip["url"]
                filename = os.path.basename(urlparse(url).path)
                
                # Clean up filename and ensure it has an extension
                filename = re.sub(r'[^\w\-_.]', '_', filename)
                if not os.path.splitext(filename)[1]:
                    filename += ".mp4"
                
                output_path = download_dir / filename
                
                # Skip if the file already exists
                if output_path.exists():
                    print(f"File already exists: {output_path}")
                    continue
                
                print(f"Downloading {i+1}/{len(clips)}: {url}")
                
                # Use yt-dlp for more reliable downloading
                ydl_opts = {
                    'outtmpl': str(output_path),
                    'quiet': True,
                    'no_warnings': True,
                    'format': 'best[ext=mp4]/best',
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                print(f"Downloaded to {output_path}")
                self.random_delay()
                
            except Exception as e:
                print(f"Failed to download {url}: {str(e)}")
    
    def scrape(self, category=None):
        """Main method to scrape clips from all sources"""
        all_clips = []
        
        for source in self.config["sources"]:
            try:
                if source["name"] == "sakugabooru":
                    clips = self.scrape_sakugabooru(source)
                elif source["name"] == "animeclips_reddit":
                    clips = self.scrape_reddit(source)
                else:
                    print(f"Unknown source: {source['name']}")
                    continue
                
                all_clips.extend(clips)
                print(f"Found {len(clips)} clips from {source['name']}")
            except Exception as e:
                print(f"Error scraping from {source['name']}: {str(e)}")
        
        # Limit total clips
        all_clips = all_clips[:self.config["download_limit"]]
        
        # Download clips
        self.download_clips(all_clips, category)
        
        return all_clips

def main():
    parser = argparse.ArgumentParser(description="Anime Clip Scraper")
    parser.add_argument("--output", "-o", help="Output directory", default="downloads")
    parser.add_argument("--config", "-c", help="Config file path", default="config.json")
    parser.add_argument("--category", help="Category to sort clips into", choices=["action", "fight", "emotional", "comedy"])
    parser.add_argument("--limit", "-l", type=int, help="Limit number of clips to download")
    
    args = parser.parse_args()
    
    scraper = AnimeClipScraper(output_dir=args.output, config_file=args.config)
    
    if args.limit:
        scraper.config["download_limit"] = args.limit
    
    scraper.scrape(category=args.category)

if __name__ == "__main__":
    main() 