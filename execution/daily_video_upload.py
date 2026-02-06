#!/usr/bin/env python3
"""
Daily Video Upload - NBA Picks

Downloads videos from Google Drive folders, matches them with descriptions
from a Google Doc, generates platform-specific captions, and uploads to
YouTube, Twitter/X, and Instagram.

See: directives/daily_video_upload.md
"""

import os
import re
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from google_helpers import read_google_doc, list_drive_folder, download_drive_file

# Load environment variables
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuration
DRIVE_FOLDER_ID = '1Rn6ueiZqoLg9NJSrBGOw0PoXANgnxN_8'
DOC_ID = '1cBJM2vG9_X91o29OjLgzuJFIBzKkAiLJliZROum160s'
UPLOAD_API = 'https://api.upload-post.com/api/upload'
UPLOAD_API_KEY = os.getenv('UPLOAD_POST_API_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InBpY2tzeXBpY2tzQHlhaG9vLmNvbSIsImV4cCI6NDkxNjkyMjExNywianRpIjoiM2E3YzliMzQtMGMxYS00NmVkLWI3OTAtMGU0MDU5M2RlMzQ5In0.xCEnWBF_00Ob3HN7e6tsGBBHaJfg4i-JdPBEZkfJNYY')

# Account mapping (includes aliases for doc vs folder name mismatches)
ACCOUNT_MAP = {
    'GRIFFIN': 'griffinSports',
    'HANS': 'hansPicks',
    'LANDON': 'landonBets',
    'LONDON': 'landonBets',  # Doc says LONDON, folder says LANDON
}

# Folders to skip
SKIP_FOLDERS = {'NADIA', 'DESCRIPTIONS'}

# Video file extensions
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v'}

# Temp directory for downloads
TMP_DIR = Path(__file__).parent.parent / '.tmp'


def parse_descriptions(doc_text: str) -> dict:
    """
    Parse the Google Doc text to extract person -> caption mapping.
    Format: Person name on its own line, followed by their caption text.
    """
    descriptions = {}
    # Include LONDON as alias for LANDON (doc may use different spelling)
    persons = ['GRIFFIN', 'HANS', 'LANDON', 'LONDON', 'NADIA']

    # Normalize line endings
    doc_text = doc_text.replace('\r\n', '\n').replace('\r', '\n')

    for person in persons:
        # Find the person's section - their name followed by content
        # Pattern: person name at start of line (possibly with whitespace)
        pattern = rf'(?:^|\n)\s*{person}\s*\n'
        match = re.search(pattern, doc_text, re.IGNORECASE)

        if match:
            start_idx = match.end()

            # Find where the next person's section starts
            end_idx = len(doc_text)
            for other_person in persons:
                if other_person != person:
                    next_pattern = rf'\n\s*{other_person}\s*\n'
                    next_match = re.search(next_pattern, doc_text[start_idx:], re.IGNORECASE)
                    if next_match:
                        potential_end = start_idx + next_match.start()
                        if potential_end < end_idx:
                            end_idx = potential_end

            caption = doc_text[start_idx:end_idx].strip()
            # Clean up excessive newlines
            caption = re.sub(r'\n{3,}', '\n\n', caption)
            descriptions[person.upper()] = caption
            print(f"  Found caption for {person}: {len(caption)} chars")

    return descriptions


def get_video_file(folder_id: str) -> dict | None:
    """Find the video file in a folder."""
    files = list_drive_folder(folder_id)

    for f in files:
        name = f.get('name', '').lower()
        ext = Path(name).suffix.lower()
        mime = f.get('mimeType', '')

        if ext in VIDEO_EXTENSIONS or mime.startswith('video/'):
            return f

    return None


def get_next_day_name() -> str:
    """Get tomorrow's day name in America/Edmonton timezone."""
    from datetime import datetime, timedelta
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo('America/Edmonton')
    except ImportError:
        import pytz
        tz = pytz.timezone('America/Edmonton')

    now = datetime.now(tz)
    tomorrow = now + timedelta(days=1)
    return tomorrow.strftime('%A')  # Returns 'Friday', 'Saturday', etc.


def generate_captions(raw_caption: str) -> dict:
    """Generate fixed captions with next day's name."""
    print(f"  Generating captions with next day...")

    next_day = get_next_day_name()
    print(f"  Next day: {next_day}")

    # Fixed caption template - replace Thursday with the actual next day
    caption_template = f"""NBA Picks for {next_day}  🚀 #NBA #basketball
{next_day} NBA Props
NBA Locks for Tonight
NBA Locks for Today
NBA Props Tonight"""

    yt_title = f"NBA Picks for {next_day}"

    return {
        'yt_title': yt_title,
        'twitter_caption': caption_template,
        'instagram_caption': caption_template,
    }


def upload_to_platforms(video_path: str, account: str, captions: dict) -> dict:
    """Upload video to all platforms via upload-post API."""
    print(f"  Uploading to platforms for account: {account}")

    with open(video_path, 'rb') as video_file:
        files = {
            'video': (Path(video_path).name, video_file, 'video/mp4')
        }

        data = {
            'user': account,
            'title': captions['yt_title'],
            'platform[]': ['youtube', 'x', 'instagram'],
            'async_upload': 'true',

            # Instagram fields
            'media_type': 'REELS',
            'share_to_feed': 'true',
            'description': captions['instagram_caption'],

            # YouTube fields
            'youtube_title': captions['yt_title'],
            'categoryId': '22',
            'privacyStatus': 'public',
            'embeddable': 'true',
            'license': 'youtube',
            'publicStatsViewable': 'true',
            'selfDeclaredMadeForKids': 'false',
            'containsSyntheticMedia': 'false',
            'hasPaidProductPlacement': 'false',

            # X/Twitter fields
            'x_long_text_as_post': 'false',
            'x_title': captions['twitter_caption'],
            'nullcast': 'false',
            'for_super_followers_only': 'false',
            'share_with_followers': 'false',
        }

        headers = {
            'Authorization': f'Apikey {UPLOAD_API_KEY}'
        }

        # Handle platform[] array properly for requests
        # requests needs multiple values for same key
        form_data = []
        for key, value in data.items():
            if key == 'platform[]':
                for platform in value:
                    form_data.append(('platform[]', platform))
            else:
                form_data.append((key, value))

        response = requests.post(
            UPLOAD_API,
            files=files,
            data=form_data,
            headers=headers,
            timeout=600  # 10 minute timeout for upload
        )

        if response.status_code == 200:
            try:
                return response.json()
            except:
                return {'status': 'success', 'raw': response.text}
        else:
            return {'status': 'error', 'code': response.status_code, 'message': response.text}


def main():
    """Main execution function."""
    print("=" * 60)
    print("Daily Video Upload - NBA Picks")
    print("=" * 60)

    # Ensure tmp directory exists
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Read and parse descriptions
    print("\n[1] Reading descriptions from Google Doc...")
    doc_text = read_google_doc(DOC_ID)
    descriptions = parse_descriptions(doc_text)
    print(f"  Parsed {len(descriptions)} descriptions")

    # Step 2: List folders in Drive
    print("\n[2] Listing folders in Google Drive...")
    items = list_drive_folder(DRIVE_FOLDER_ID)
    folders = [
        f for f in items
        if f.get('mimeType') == 'application/vnd.google-apps.folder'
        and f.get('name', '').upper() not in SKIP_FOLDERS
    ]
    print(f"  Found {len(folders)} folders to process: {[f['name'] for f in folders]}")

    # Step 3: Process each folder
    results = []
    for folder in folders:
        folder_name = folder['name'].strip().upper()  # Strip whitespace
        folder_id = folder['id']

        print(f"\n[3] Processing {folder_name}...")

        # Get account
        account = ACCOUNT_MAP.get(folder_name)
        if not account:
            print(f"  Warning: No account mapping for {folder_name}, skipping")
            continue

        # Get caption (check aliases: LANDON <-> LONDON)
        caption = descriptions.get(folder_name, '')
        if not caption and folder_name == 'LANDON':
            caption = descriptions.get('LONDON', '')
        if not caption and folder_name == 'LONDON':
            caption = descriptions.get('LANDON', '')
        if not caption:
            print(f"  Warning: No caption found for {folder_name}, using folder name")
            caption = f"{folder_name} NBA Picks"

        # Find video file
        video_file = get_video_file(folder_id)
        if not video_file:
            print(f"  Warning: No video file found in {folder_name}, skipping")
            continue

        print(f"  Found video: {video_file['name']}")

        # Download video
        video_path = TMP_DIR / f"{folder_name}_{video_file['name']}"
        print(f"  Downloading to {video_path}...")
        download_drive_file(video_file['id'], str(video_path))

        # Generate platform captions
        captions = generate_captions(caption)
        print(f"  Generated captions:")
        print(f"    YT Title: {captions['yt_title'][:50]}...")

        # Upload to platforms
        result = upload_to_platforms(str(video_path), account, captions)
        results.append({
            'folder': folder_name,
            'account': account,
            'result': result
        })

        print(f"  Upload result: {result.get('status', 'unknown')}")

        # Clean up downloaded file
        try:
            video_path.unlink()
            print(f"  Cleaned up temp file")
        except:
            pass

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        status = r['result'].get('status', r['result'].get('request_id', 'unknown'))
        print(f"  {r['folder']} ({r['account']}): {status}")

    return results


if __name__ == '__main__':
    main()
