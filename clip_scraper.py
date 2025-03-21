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

# Import super resolution if available
try:
    from super_resolution import SuperResolution, HAS_REALESRGAN
except ImportError:
    HAS_REALESRGAN = False

class AnimeClipScraper:
    def __init__(self, output_dir="downloads", config_file="config.json"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.config_file = config_file
        self.load_config()
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Initialize super resolution if enabled
        self.super_resolution = None
        if self.config.get("enhance_videos", False) and HAS_REALESRGAN:
            try:
                self.super_resolution = SuperResolution(
                    model_name=self.config.get("sr_model", "realesr-animevideov3"),
                    device=self.config.get("sr_device", "auto"),
                    scale=self.config.get("sr_scale", 2),
                    denoise_strength=self.config.get("sr_denoise", 0.5)
                )
                print("Super resolution initialized successfully")
            except Exception as e:
                print(f"Failed to initialize super resolution: {str(e)}")
                self.super_resolution = None
        
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
                        "name": "youtube_anime",
                        "search_term": "anime fight scenes",
                        "max_results": 10,
                        "min_duration": 10,  # Minimum duration in seconds
                        "max_duration": 180  # Maximum duration in seconds (3 minutes)
                    },
                    {
                        "name": "sakugabooru",
                        "base_url": "https://www.sakugabooru.com/post?tags=animated+mp4",  # Prioritize MP4 content
                        "page_param": "page={}",
                        "clip_selector": "article.post-preview",
                        "link_selector": "a.directlink",
                        "next_page_selector": "a.next_page",
                        "max_pages": 3
                    },
                    {
                        "name": "animeclips_reddit",
                        "base_url": "https://www.reddit.com/r/AnimeSakuga/hot/.json",  # Better subreddit for animation clips
                        "is_api": True,
                        "max_items": 20
                    },
                    {
                        "name": "tenor_anime",
                        "base_url": "https://tenor.com/search/anime-gifs",
                        "search_term": "anime",
                        "clip_selector": "div.GifList div.Gif",
                        "link_selector": "img.GifListItem",
                        "max_pages": 2
                    }
                ],
                "download_limit": 10,
                "min_delay": 1,
                "max_delay": 3,
                "categories": ["action", "fight", "emotional", "comedy"],
                "prefer_video": True,  # Prefer video content over GIFs
                "enhance_videos": False,  # Whether to enhance videos with super resolution
                "sr_model": "realesr-animevideov3",  # Super resolution model
                "sr_scale": 2,  # Scale factor for super resolution
                "sr_denoise": 0.5,  # Denoise strength for super resolution
                "sr_device": "auto"  # Device for super resolution (auto, cuda, cpu)
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
            
            # Skip if not a media link or if it's a gallery
            if not url or "gallery" in url:
                continue
            
            # For v.redd.it links, get the actual media URL
            if "v.redd.it" in url:
                fallback_url = post_data.get("secure_media", {}).get("reddit_video", {}).get("fallback_url")
                if fallback_url:
                    url = fallback_url
            
            # Direct links to images and videos
            if url.endswith(('.mp4', '.gif', '.webm', '.jpg', '.jpeg', '.png')):
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
    
    def scrape_youtube(self, source):
        """Scrape anime video clips from YouTube"""
        clips = []
        search_term = source.get("search_term", "anime clips")
        max_results = source.get("max_results", 10)
        min_duration = source.get("min_duration", 10)  # Default 10 seconds minimum
        max_duration = source.get("max_duration", 180)  # Default 3 minutes maximum
        
        print(f"Searching YouTube for '{search_term}'...")
        
        try:
            # Use yt-dlp for search
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'force_generic_extractor': False,
                'format': 'best[ext=mp4]/best',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_url = f"ytsearch{max_results*2}:{search_term}"  # Search for twice as many to filter
                search_results = ydl.extract_info(search_url, download=False)
                
                if not search_results or 'entries' not in search_results:
                    print("No YouTube search results found")
                    return clips
                
                # Process each search result
                for entry in search_results['entries']:
                    try:
                        if not entry or entry.get('_type') == 'playlist':
                            continue
                        
                        video_id = entry.get('id')
                        if not video_id:
                            continue
                        
                        # Get more detailed info about the video
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        detailed_info = ydl.extract_info(video_url, download=False)
                        
                        # Check duration
                        duration = detailed_info.get('duration')
                        if duration and (duration < min_duration or duration > max_duration):
                            continue
                        
                        # Add to clips list
                        clips.append({
                            "source": "youtube",
                            "url": video_url,
                            "title": detailed_info.get('title', ''),
                            "duration": duration,
                            "thumbnail": detailed_info.get('thumbnail', ''),
                            "tags": detailed_info.get('tags', [])
                        })
                        
                        print(f"Found YouTube clip: {detailed_info.get('title', 'Untitled')} ({duration}s)")
                        
                        if len(clips) >= max_results:
                            break
                            
                    except Exception as e:
                        print(f"Error processing YouTube result: {str(e)}")
                        continue
        
        except Exception as e:
            print(f"Error scraping YouTube: {str(e)}")
        
        return clips[:source.get("max_results", 10)]
    
    def scrape_tenor(self, source):
        """Scrape anime GIFs from Tenor"""
        clips = []
        
        search_term = source.get("search_term", "anime")
        base_url = source["base_url"]
        
        # If base_url doesn't already include the search term, add it
        if search_term not in base_url:
            base_url = f"https://tenor.com/search/{search_term}-gifs"
        
        print(f"Scraping {source['name']} for '{search_term}' GIFs...")
        
        try:
            response = requests.get(base_url, headers=self.headers)
            
            if response.status_code != 200:
                print(f"Failed to fetch {base_url}, status code: {response.status_code}")
                return clips
            
            soup = BeautifulSoup(response.text, 'html.parser')
            gif_elements = soup.select(source["clip_selector"])
            
            print(f"Found {len(gif_elements)} GIF elements")
            
            for element in gif_elements:
                try:
                    # Extract the image source
                    img_element = element.select_one(source["link_selector"])
                    if not img_element:
                        continue
                    
                    # Get image source, which might be in src or data-src attribute
                    src = img_element.get('src') or img_element.get('data-src')
                    if not src:
                        continue
                    
                    # Tenor typically serves WebP images, but we want the GIF
                    # Convert the URL to get the GIF version
                    if "tenor.com" in src and not src.endswith('.gif'):
                        # Example: https://media.tenor.com/images/xyz/tenor.gif
                        gif_id = None
                        
                        # Extract GIF ID from various formats
                        if "/images/" in src:
                            parts = src.split("/")
                            for i, part in enumerate(parts):
                                if part == "images" and i+1 < len(parts):
                                    gif_id = parts[i+1]
                                    break
                        
                        if gif_id:
                            src = f"https://media.tenor.com/images/{gif_id}/tenor.gif"
                    
                    # Only add GIF URLs
                    if src.lower().endswith('.gif'):
                        # Get title if available
                        alt_text = img_element.get('alt', '')
                        title = alt_text if alt_text and alt_text != "tenor" else f"tenor_gif_{len(clips)}"
                        
                        clips.append({
                            "source": source["name"],
                            "url": src,
                            "title": title,
                            "tags": ["anime", search_term]
                        })
                        
                        if len(clips) >= self.config["download_limit"]:
                            break
                
                except Exception as e:
                    print(f"Error processing Tenor GIF: {str(e)}")
            
            print(f"Successfully extracted {len(clips)} GIF URLs from Tenor")
        
        except Exception as e:
            print(f"Error scraping Tenor: {str(e)}")
        
        return clips[:self.config["download_limit"]]
    
    def download_clips(self, clips, category=None):
        """Download clips to the output directory"""
        download_dir = self.output_dir
        if category:
            download_dir = self.output_dir / category
            download_dir.mkdir(exist_ok=True)
        
        # Sort clips to prioritize videos over GIFs if the config specifies
        if self.config.get("prefer_video", True):
            # Move video clips to the front
            clips.sort(key=lambda x: 0 if x["url"].lower().endswith(('.mp4', '.webm')) else 
                                  (1 if "youtube.com" in x["url"].lower() else 2))
        
        # Track downloaded videos for super resolution
        downloaded_videos = []
        
        for i, clip in enumerate(clips):
            try:
                url = clip["url"]
                
                # For YouTube URLs, use the video ID and title for filename
                if "youtube.com" in url or "youtu.be" in url:
                    video_id = None
                    if "youtube.com/watch" in url and "v=" in url:
                        video_id = url.split("v=")[1].split("&")[0]
                    elif "youtu.be/" in url:
                        video_id = url.split("youtu.be/")[1].split("?")[0]
                    
                    if video_id and clip.get("title"):
                        # Clean up title for filename
                        clean_title = re.sub(r'[^\w\-_. ]', '_', clip.get("title"))
                        clean_title = clean_title[:50]  # Limit length
                        filename = f"{clean_title}_{video_id}.mp4"
                    else:
                        filename = os.path.basename(urlparse(url).path)
                else:
                    filename = os.path.basename(urlparse(url).path)
                
                # Clean up filename and ensure it has an extension
                filename = re.sub(r'[^\w\-_.]', '_', filename)
                if not os.path.splitext(filename)[1]:
                    filename += ".mp4"
                
                output_path = download_dir / filename
                
                # Skip if the file already exists
                if output_path.exists():
                    print(f"File already exists: {output_path}")
                    if output_path.suffix.lower() in ['.mp4', '.webm', '.mkv']:
                        downloaded_videos.append(str(output_path))
                    continue
                
                print(f"Downloading {i+1}/{len(clips)}: {url}")
                
                # For direct image files (GIF, etc.), use requests instead of yt-dlp
                if url.lower().endswith(('.gif', '.jpg', '.jpeg', '.png')):
                    # If we prefer videos and have reached at least half our limit, skip images
                    if self.config.get("prefer_video", True) and i >= (self.config["download_limit"] // 2):
                        print(f"Skipping image file (preferring videos): {url}")
                        continue
                    
                    try:
                        # Follow redirects to get the actual content
                        response = requests.get(url, headers=self.headers, stream=True, allow_redirects=True)
                        if response.status_code == 200:
                            with open(output_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"Downloaded to {output_path}")
                        else:
                            print(f"Failed to download {url}: HTTP status {response.status_code}")
                    except Exception as e:
                        print(f"Failed to download {url} using direct method: {str(e)}")
                        # Try fallback with yt-dlp
                        try:
                            ydl_opts = {
                                'outtmpl': str(output_path),
                                'quiet': True,
                                'no_warnings': True,
                                'format': 'best[ext=mp4]/best',
                            }
                            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                                ydl.download([url])
                            print(f"Downloaded to {output_path} using yt-dlp fallback")
                        except Exception as e2:
                            print(f"Fallback also failed: {str(e2)}")
                else:
                    # Use yt-dlp for video content
                    ydl_opts = {
                        'outtmpl': str(output_path),
                        'quiet': True,
                        'no_warnings': True,
                        'format': 'best[ext=mp4]/best',
                        'merge_output_format': 'mp4',
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    
                    print(f"Downloaded to {output_path}")
                    if output_path.suffix.lower() in ['.mp4', '.webm', '.mkv']:
                        downloaded_videos.append(str(output_path))
                
                self.random_delay()
                
            except Exception as e:
                print(f"Failed to download {url}: {str(e)}")
        
        # Apply super resolution to downloaded videos if enabled
        if self.super_resolution and self.config.get("enhance_videos", False) and downloaded_videos:
            print(f"\nEnhancing {len(downloaded_videos)} videos with super resolution...")
            for video_path in downloaded_videos:
                try:
                    # Process the video with super resolution
                    output_path = Path(video_path).parent / (Path(video_path).stem + f"_enhanced{Path(video_path).suffix}")
                    # Only process if enhanced version doesn't exist
                    if not output_path.exists():
                        print(f"Enhancing: {video_path}")
                        self.super_resolution.process_video(video_path, output_path)
                    else:
                        print(f"Enhanced version already exists: {output_path}")
                except Exception as e:
                    print(f"Failed to enhance {video_path}: {str(e)}")
    
    def scrape(self, category=None):
        """Main method to scrape clips from all sources"""
        all_clips = []
        
        for source in self.config["sources"]:
            try:
                if source["name"] == "sakugabooru":
                    clips = self.scrape_sakugabooru(source)
                elif source["name"] == "animeclips_reddit":
                    clips = self.scrape_reddit(source)
                elif source["name"] == "tenor_anime":
                    # Skip Tenor if prefer_video is True
                    if self.config.get("prefer_video", True):
                        print(f"Skipping {source['name']} since video content is preferred")
                        continue
                    clips = self.scrape_tenor(source)
                elif source["name"] == "youtube_anime":
                    clips = self.scrape_youtube(source)
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
    parser.add_argument("--search", "-s", help="Search term for YouTube videos")
    parser.add_argument("--prefer-video", action="store_true", help="Prefer video content over GIFs")
    parser.add_argument("--enhance", "-e", action="store_true", help="Enhance videos with super resolution")
    parser.add_argument("--sr-scale", type=int, choices=[2, 3, 4], default=2, help="Scale factor for super resolution")
    parser.add_argument("--sr-denoise", type=float, default=0.5, help="Denoise strength for super resolution (0.0 to 1.0)")
    parser.add_argument("--sr-model", choices=["anime", "general"], default="anime", help="Super resolution model to use")
    parser.add_argument("--enhance-only", help="Enhance existing videos in directory without downloading new ones")
    
    args = parser.parse_args()
    
    scraper = AnimeClipScraper(output_dir=args.output, config_file=args.config)
    
    if args.limit:
        scraper.config["download_limit"] = args.limit
    
    if args.prefer_video:
        scraper.config["prefer_video"] = True
    
    # Update super resolution settings if provided
    if args.enhance:
        scraper.config["enhance_videos"] = True
        
        if args.sr_scale:
            scraper.config["sr_scale"] = args.sr_scale
            
        if args.sr_denoise:
            scraper.config["sr_denoise"] = args.sr_denoise
            
        if args.sr_model:
            scraper.config["sr_model"] = "realesr-animevideov3" if args.sr_model == "anime" else "realesrgan-x4plus"
            
        # Reinitialize super resolution with new settings
        if HAS_REALESRGAN:
            try:
                scraper.super_resolution = SuperResolution(
                    model_name=scraper.config.get("sr_model", "realesr-animevideov3"),
                    device=scraper.config.get("sr_device", "auto"),
                    scale=scraper.config.get("sr_scale", 2),
                    denoise_strength=scraper.config.get("sr_denoise", 0.5)
                )
            except Exception as e:
                print(f"Failed to initialize super resolution: {str(e)}")
                if args.enhance or args.enhance_only:
                    print("Cannot proceed with enhancement. Exiting.")
                    sys.exit(1)
    
    # If enhance-only mode is active, just enhance existing videos
    if args.enhance_only:
        if not HAS_REALESRGAN or not scraper.super_resolution:
            print("Super resolution is not available. Please install the required dependencies.")
            sys.exit(1)
            
        enhance_dir = Path(args.enhance_only)
        if not enhance_dir.exists() or not enhance_dir.is_dir():
            print(f"Directory does not exist: {enhance_dir}")
            sys.exit(1)
            
        print(f"Enhancing existing videos in {enhance_dir}...")
        scraper.super_resolution.batch_process_directory(
            enhance_dir, 
            file_types=('.mp4', '.webm', '.mkv'),
            recursive=True
        )
        sys.exit(0)
    
    # If search term is provided, add/update YouTube source
    if args.search:
        youtube_source = None
        
        # Find existing YouTube source or create new one
        for source in scraper.config["sources"]:
            if source["name"] == "youtube_anime":
                youtube_source = source
                break
        
        if not youtube_source:
            youtube_source = {
                "name": "youtube_anime",
                "max_results": scraper.config["download_limit"],
                "min_duration": 10,
                "max_duration": 180
            }
            scraper.config["sources"].insert(0, youtube_source)
        
        youtube_source["search_term"] = args.search
    
    scraper.scrape(category=args.category)

if __name__ == "__main__":
    main() 