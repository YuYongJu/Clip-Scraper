# Anime Clip Scraper

A Python-based tool for automatically scraping and downloading anime clips from various sources on the web to streamline your video editing workflow.

## Features

- Scrapes anime clips from multiple sources:
  - Sakugabooru (animation gallery)
  - Reddit r/animegifs
- Automatically downloads and organizes clips
- Configurable via JSON
- Categories for organizing clips (action, fight, emotional, comedy)
- Rate limiting to avoid getting blocked
- Utilities for adding new sources and organizing clips

## Requirements

- Python 3.6+
- Libraries: requests, beautifulsoup4, yt-dlp, python-dotenv

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

## Usage

### Basic Usage

To run the scraper with default settings:

```
python clip_scraper.py
```

This will download clips to the `downloads` directory.

### Command-line Options

- `--output`, `-o`: Specify the output directory (default: `downloads`)
- `--config`, `-c`: Specify a custom config file (default: `config.json`)
- `--category`: Sort clips into a specific category folder (action, fight, emotional, comedy)
- `--limit`, `-l`: Limit the number of clips to download

Example:
```
python clip_scraper.py --output my_clips --category action --limit 5
```

### Configuration

The scraper creates a `config.json` file on first run with default settings. You can edit this file to:

- Add or modify sources
- Change download limits
- Adjust delay between requests
- Define custom categories

Example config.json:
```json
{
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
            "is_api": true,
            "max_items": 20
        }
    ],
    "download_limit": 10,
    "min_delay": 1,
    "max_delay": 3,
    "categories": ["action", "fight", "emotional", "comedy"]
}
```

## Additional Utilities

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

## Workflow Example

Here's a recommended workflow for using this scraper for video editing:

1. Run the scraper to download clips:
   ```
   python clip_scraper.py --limit 20
   ```

2. Auto-categorize clips by type:
   ```
   python organize_clips.py auto
   ```

3. Manually categorize any remaining clips:
   ```
   python organize_clips.py interactive
   ```

4. Rename clips in your chosen category for better organization:
   ```
   python organize_clips.py --directory downloads/action rename --prefix "action" --numbered
   ```

5. Import the organized clips into your video editing software and start creating!

## Customizing Sources

To add a new source, you can either:
1. Use the `add_source.py` utility
2. Edit the config.json file directly
3. Add implementation to the AnimeClipScraper class in clip_scraper.py

## Legal Disclaimer

This tool is intended for personal use only. Please respect copyright laws and website terms of service. Only download content that you have the right to use. 