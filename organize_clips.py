#!/usr/bin/env python3
import os
import json
import shutil
import argparse
from pathlib import Path
import re

def load_config(config_file):
    """Load the configuration file"""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        print(f"Config file {config_file} not found.")
        return None

def list_clips(directory):
    """List all video clips in the specified directory"""
    clips = []
    for ext in ['.mp4', '.webm', '.gif']:
        clips.extend(list(Path(directory).glob(f'**/*{ext}')))
    
    return sorted(clips)

def list_categories(config):
    """List available categories from config"""
    return config.get("categories", [])

def create_category_dirs(base_dir, categories):
    """Create directories for each category"""
    for category in categories:
        category_dir = Path(base_dir) / category
        category_dir.mkdir(exist_ok=True)
        print(f"Created directory: {category_dir}")

def move_clip(clip_path, dest_dir):
    """Move a clip to a specified destination directory"""
    dest_path = Path(dest_dir) / clip_path.name
    
    # If the file already exists in the destination, add a suffix
    if dest_path.exists():
        base_name = dest_path.stem
        extension = dest_path.suffix
        counter = 1
        
        while dest_path.exists():
            new_name = f"{base_name}_{counter}{extension}"
            dest_path = dest_path.parent / new_name
            counter += 1
    
    # Move the file
    shutil.move(str(clip_path), str(dest_path))
    print(f"Moved: {clip_path.name} -> {dest_path}")
    
    return dest_path

def interactive_categorize(clips, categories, base_dir):
    """Interactive mode to categorize clips"""
    for i, clip in enumerate(clips):
        print(f"\nClip {i+1}/{len(clips)}: {clip.name}")
        
        # List available categories
        print("Available categories:")
        for j, category in enumerate(categories, 1):
            print(f"{j}. {category}")
        print("0. Skip this clip")
        print("q. Quit")
        
        choice = input("Choose a category (number or q): ").strip().lower()
        
        if choice == 'q':
            print("Quitting...")
            break
        
        try:
            choice_num = int(choice)
            if choice_num == 0:
                print(f"Skipped: {clip.name}")
                continue
                
            if 1 <= choice_num <= len(categories):
                selected_category = categories[choice_num-1]
                dest_dir = Path(base_dir) / selected_category
                move_clip(clip, dest_dir)
            else:
                print("Invalid category number.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q'.")

def batch_categorize(clips, category, base_dir):
    """Move all clips to a specific category"""
    dest_dir = Path(base_dir) / category
    
    for clip in clips:
        move_clip(clip, dest_dir)
    
    print(f"\nMoved {len(clips)} clips to '{category}' category.")

def auto_categorize_by_name(clips, categories, base_dir):
    """Auto-categorize clips based on filename keywords"""
    # Create a dictionary of category keywords
    category_keywords = {
        "action": ["action", "fight", "battle", "explosion", "combat"],
        "fight": ["fight", "battle", "duel", "combat", "vs", "versus"],
        "emotional": ["sad", "cry", "tear", "emotional", "drama", "love"],
        "comedy": ["funny", "comedy", "laugh", "humor", "joke", "gag"]
    }
    
    # Update with user-defined categories
    for category in categories:
        if category not in category_keywords:
            category_keywords[category] = [category.lower()]
    
    categorized = 0
    
    for clip in clips:
        filename = clip.stem.lower()
        
        # Try to find matching category
        matched_category = None
        for category, keywords in category_keywords.items():
            if any(keyword in filename for keyword in keywords):
                matched_category = category
                break
        
        if matched_category and matched_category in categories:
            dest_dir = Path(base_dir) / matched_category
            move_clip(clip, dest_dir)
            categorized += 1
    
    print(f"\nAuto-categorized {categorized} clips based on filename.")
    return categorized

def rename_clips(clips, prefix=None, numbered=False):
    """Rename clips with optional prefix and numbering"""
    for i, clip in enumerate(clips):
        original_name = clip.name
        extension = clip.suffix
        
        if prefix and numbered:
            new_name = f"{prefix}_{i+1:03d}{extension}"
        elif prefix:
            new_name = f"{prefix}_{clip.stem}{extension}"
        elif numbered:
            new_name = f"{i+1:03d}{extension}"
        else:
            continue  # No renaming needed
        
        new_path = clip.parent / new_name
        
        # Rename the file
        clip.rename(new_path)
        print(f"Renamed: {original_name} -> {new_name}")

def main():
    parser = argparse.ArgumentParser(description="Organize anime clips into categories")
    parser.add_argument("--config", "-c", help="Config file path", default="config.json")
    parser.add_argument("--directory", "-d", help="Directory containing clips", default="downloads")
    
    subparsers = parser.add_subparsers(dest="action", help="Action to perform")
    
    # List clips
    list_parser = subparsers.add_parser("list", help="List all available clips")
    
    # Interactive categorization
    interactive_parser = subparsers.add_parser("interactive", help="Interactively categorize clips")
    
    # Batch categorization
    batch_parser = subparsers.add_parser("batch", help="Move all clips to a specific category")
    batch_parser.add_argument("--category", required=True, help="Category to move clips to")
    
    # Auto-categorization
    auto_parser = subparsers.add_parser("auto", help="Auto-categorize clips based on filename")
    
    # Rename clips
    rename_parser = subparsers.add_parser("rename", help="Rename clips")
    rename_parser.add_argument("--prefix", help="Prefix for renamed files")
    rename_parser.add_argument("--numbered", action="store_true", help="Number the files sequentially")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    if not config:
        return
    
    categories = list_categories(config)
    base_dir = args.directory
    
    # Ensure category directories exist
    create_category_dirs(base_dir, categories)
    
    # Get all clips
    clips = list_clips(base_dir)
    
    if args.action == "list" or not args.action:
        print(f"Found {len(clips)} clips:")
        for i, clip in enumerate(clips, 1):
            print(f"{i}. {clip}")
    
    elif args.action == "interactive":
        if not clips:
            print("No clips found in the specified directory.")
            return
        interactive_categorize(clips, categories, base_dir)
    
    elif args.action == "batch":
        if args.category not in categories:
            print(f"Error: '{args.category}' is not a valid category. Valid categories: {', '.join(categories)}")
            return
        
        if not clips:
            print("No clips found in the specified directory.")
            return
        
        batch_categorize(clips, args.category, base_dir)
    
    elif args.action == "auto":
        if not clips:
            print("No clips found in the specified directory.")
            return
        
        count = auto_categorize_by_name(clips, categories, base_dir)
        if count == 0:
            print("No clips were auto-categorized. Consider using interactive mode.")
    
    elif args.action == "rename":
        if not clips:
            print("No clips found in the specified directory.")
            return
        
        if not args.prefix and not args.numbered:
            print("Error: Provide at least one of --prefix or --numbered for renaming.")
            return
        
        rename_clips(clips, args.prefix, args.numbered)

if __name__ == "__main__":
    main() 