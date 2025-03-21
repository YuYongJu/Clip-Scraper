# Anime Clip Scraper

A Python-based tool for automatically scraping and downloading anime video clips from various sources on the web to streamline your video editing workflow.

## Features

- Scrapes anime clips from multiple sources:
  - YouTube anime videos and fight scenes
  - Sakugabooru (animation gallery, prioritizing MP4 videos)
  - Reddit r/AnimeSakuga (focused on high-quality animation)
  - Tenor GIFs (optional, disabled by default when preferring videos)
- Automatically downloads and organizes clips
- AI-powered super resolution to enhance video quality
- Configurable via JSON
- Video-first approach with option to include GIFs
- Categories for organizing clips (action, fight, emotional, comedy)
- Rate limiting to avoid getting blocked
- Utilities for adding new sources and organizing clips

## Requirements

- Python 3.6+
- Libraries: requests, beautifulsoup4, yt-dlp, python-dotenv
- For AI super resolution: torch, torchvision, opencv-python, realesrgan

## Installation

1. Clone this repository:
```
git clone https://github.com/yourusername/Clip-Scraper.git
cd Clip-Scraper
```

2. Install the required dependencies:
```
pip install -r requirements.txt
```

3. For super resolution features (optional but recommended):
```
# For NVIDIA GPU users
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
# For CPU-only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

## Usage

### Basic Usage

To run the scraper with default settings (prioritizing videos):

```
python clip_scraper.py
```

This will download video clips to the `downloads` directory.

### Command-line Options

- `--output`, `-o`: Specify the output directory (default: `downloads`)
- `--config`, `-c`: Specify a custom config file (default: `config.json`)
- `--category`: Sort clips into a specific category folder (action, fight, emotional, comedy)
- `--limit`, `-l`: Limit the number of clips to download
- `--search`, `-s`: Specify a custom YouTube search term for anime clips
- `--prefer-video`: Prioritize video content over GIFs (enabled by default)
- `--enhance`, `-e`: Enable AI super resolution to enhance downloaded videos
- `--sr-scale`: Scale factor for super resolution (2, 3, or 4, default: 2)
- `--sr-denoise`: Denoise strength (0.0 to 1.0, default: 0.5)
- `--sr-model`: Super resolution model to use (anime or general, default: anime)
- `--enhance-only`: Process existing videos in a directory with super resolution (without downloading new clips)

Example:
```
python clip_scraper.py --output my_clips --category action --limit 5 --search "anime mecha fights" --enhance --sr-scale 2
```

### AI Super Resolution

The scraper includes AI-powered super resolution to enhance your anime clips:

```
# Download and enhance videos in one step
python clip_scraper.py --search "anime fight scenes" --enhance

# Enhance videos with 4x upscaling
python clip_scraper.py --search "anime scenes" --enhance --sr-scale 4

# Only enhance existing videos (no downloading)
python clip_scraper.py --enhance-only downloads/action
```

The super resolution feature uses [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN), an AI model specifically trained to upscale anime-style content. It can:

- Upscale videos by 2x, 3x, or 4x
- Improve overall sharpness and detail
- Remove compression artifacts and noise
- Process entire directories of videos

GPU acceleration is supported and recommended for faster processing.

### YouTube Search

The scraper can find anime video clips from YouTube by providing a search term:

```
python clip_scraper.py --search "anime emotional scenes"
```

This will search YouTube for your specified term and download videos that match your criteria. The scraper is configured to look for videos between 10 seconds and 3 minutes by default.

### Configuration

The scraper creates a `config.json` file on first run with default settings. You can edit this file to:

- Add or modify sources
- Change download limits
- Adjust delay between requests
- Define custom categories
- Set video duration preferences
- Configure super resolution settings

Example config.json:
```json
{
    "sources": [
        {
            "name": "youtube_anime",
            "search_term": "anime fight scenes",
            "max_results": 10,
            "min_duration": 10,
            "max_duration": 180
        },
        {
            "name": "sakugabooru",
            "base_url": "https://www.sakugabooru.com/post?tags=animated+mp4",
            "page_param": "page={}",
            "clip_selector": "article.post-preview",
            "link_selector": "a.directlink",
            "next_page_selector": "a.next_page",
            "max_pages": 3
        },
        {
            "name": "animeclips_reddit",
            "base_url": "https://www.reddit.com/r/AnimeSakuga/hot/.json",
            "is_api": true,
            "max_items": 20
        }
    ],
    "download_limit": 10,
    "min_delay": 1,
    "max_delay": 3,
    "categories": ["action", "fight", "emotional", "comedy"],
    "prefer_video": true,
    "enhance_videos": false,
    "sr_model": "realesr-animevideov3",
    "sr_scale": 2,
    "sr_denoise": 0.5,
    "sr_device": "auto"
}
```

## Additional Utilities

### Super Resolution Command Line Tool

You can also use the super resolution module directly:

```
# Enhance a single video
python super_resolution.py input_video.mp4 --scale 2 --model anime

# Process all videos in a directory
python super_resolution.py input_directory --batch --scale 2

# Use a specific output directory
python super_resolution.py input_video.mp4 --output enhanced/output.mp4
```

### Adding Custom Sources

Use the `add_source.py` script to easily add new sources to your configuration:

```
# Add an HTML-based source
python add_source.py html --name "your_source" --url "https://example.com/clips" --clip-selector "div.clip" --link-selector "a.video-link" --next-page "a.next" --page-param "page={}" --max-pages 5

# Add an API-based source
python add_source.py api --name "your_api" --url "https://api.example.com/clips" --max-items 30

# List all configured sources
python add_source.py list
```

### Organizing Clips

Use the `organize_clips.py` script to sort and manage downloaded clips:

```
# List all clips
python organize_clips.py list

# Interactively categorize clips
python organize_clips.py interactive

# Move all clips to a specific category
python organize_clips.py batch --category action

# Automatically categorize clips based on filename
python organize_clips.py auto

# Rename clips with a prefix and/or numbering
python organize_clips.py rename --prefix "anime" --numbered
```

## Workflow Example for Video Editing

Here's a recommended workflow for using this scraper for video editing:

1. Run the scraper with a specific search term to find relevant video clips:
   ```
   python clip_scraper.py --search "anime fight scenes sakuga" --limit 20
   ```

2. Add more clips from a different theme:
   ```
   python clip_scraper.py --search "anime emotional moments" --output downloads/emotional --category emotional
   ```

3. Enhance the videos with AI super resolution:
   ```
   python clip_scraper.py --enhance-only downloads --sr-scale 2
   ```

4. Auto-categorize clips by type:
   ```
   python organize_clips.py auto
   ```

5. Manually categorize any remaining clips:
   ```
   python organize_clips.py interactive
   ```

6. Rename clips in your chosen category for better organization:
   ```
   python organize_clips.py --directory downloads/action rename --prefix "action" --numbered
   ```

7. Import the enhanced, organized clips into your video editing software and start creating!

## Customizing Sources

To add a new source, you can either:
1. Use the `add_source.py` utility
2. Edit the config.json file directly
3. Add implementation to the AnimeClipScraper class in clip_scraper.py

## Legal Disclaimer

This tool is intended for personal use only. Please respect copyright laws and website terms of service. Only download content that you have the right to use. 