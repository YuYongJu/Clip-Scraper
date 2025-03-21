#!/usr/bin/env python3
import json
import os
import argparse
from pathlib import Path

def load_config(config_file):
    """Load the configuration file or create with defaults"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Default empty config
        default_config = {
            "sources": [],
            "download_limit": 10,
            "min_delay": 1,
            "max_delay": 3,
            "categories": ["action", "fight", "emotional", "comedy"]
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

def save_config(config, config_file):
    """Save configuration to file"""
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"Configuration saved to {config_file}")

def add_html_source(config, name, base_url, clip_selector, link_selector, 
                  next_page_selector=None, page_param=None, max_pages=3):
    """Add a new HTML-based source to the configuration"""
    # Check if source already exists
    for source in config["sources"]:
        if source["name"] == name:
            print(f"Source with name '{name}' already exists. Please use a unique name.")
            return False
    
    new_source = {
        "name": name,
        "base_url": base_url,
        "clip_selector": clip_selector,
        "link_selector": link_selector
    }
    
    if next_page_selector:
        new_source["next_page_selector"] = next_page_selector
    
    if page_param:
        new_source["page_param"] = page_param
    
    new_source["max_pages"] = max_pages
    
    config["sources"].append(new_source)
    return True

def add_api_source(config, name, base_url, max_items=20):
    """Add a new API-based source to the configuration"""
    # Check if source already exists
    for source in config["sources"]:
        if source["name"] == name:
            print(f"Source with name '{name}' already exists. Please use a unique name.")
            return False
    
    new_source = {
        "name": name,
        "base_url": base_url,
        "is_api": True,
        "max_items": max_items
    }
    
    config["sources"].append(new_source)
    return True

def main():
    parser = argparse.ArgumentParser(description="Add a new source to Anime Clip Scraper")
    parser.add_argument("--config", "-c", help="Config file path", default="config.json")
    
    subparsers = parser.add_subparsers(dest="source_type", help="Type of source to add")
    
    # HTML parser
    html_parser = subparsers.add_parser("html", help="Add an HTML-based source")
    html_parser.add_argument("--name", required=True, help="Name of the source")
    html_parser.add_argument("--url", required=True, help="Base URL of the source")
    html_parser.add_argument("--clip-selector", required=True, help="CSS selector for clip containers")
    html_parser.add_argument("--link-selector", required=True, help="CSS selector for the video link")
    html_parser.add_argument("--next-page", help="CSS selector for the next page link")
    html_parser.add_argument("--page-param", help="URL parameter format for pagination (e.g., 'page={}')")
    html_parser.add_argument("--max-pages", type=int, default=3, help="Maximum number of pages to scrape")
    
    # API parser
    api_parser = subparsers.add_parser("api", help="Add an API-based source")
    api_parser.add_argument("--name", required=True, help="Name of the source")
    api_parser.add_argument("--url", required=True, help="Base URL of the API endpoint")
    api_parser.add_argument("--max-items", type=int, default=20, help="Maximum number of items to retrieve")
    
    # List parser
    list_parser = subparsers.add_parser("list", help="List all configured sources")
    
    args = parser.parse_args()
    
    config_file = args.config
    config = load_config(config_file)
    
    if args.source_type == "html":
        success = add_html_source(
            config,
            args.name,
            args.url,
            args.clip_selector,
            args.link_selector,
            args.next_page,
            args.page_param,
            args.max_pages
        )
        if success:
            save_config(config, config_file)
            print(f"HTML source '{args.name}' added successfully.")
    
    elif args.source_type == "api":
        success = add_api_source(
            config,
            args.name,
            args.url,
            args.max_items
        )
        if success:
            save_config(config, config_file)
            print(f"API source '{args.name}' added successfully.")
    
    elif args.source_type == "list" or not args.source_type:
        print("Configured sources:")
        for i, source in enumerate(config["sources"], 1):
            source_type = "API" if source.get("is_api", False) else "HTML"
            print(f"{i}. {source['name']} ({source_type}): {source['base_url']}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 