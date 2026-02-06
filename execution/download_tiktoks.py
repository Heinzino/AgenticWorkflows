#!/usr/bin/env python3
"""
Download TikTok videos from a Google Sheet and upload to Google Drive.

Reads player names and TikTok URLs from a sheet, downloads videos via tdown.app API,
and uploads them to the corresponding player folder in Google Drive.

Usage:
    python download_tiktoks.py --sheet-id <id> --folder-id <id> [--dry-run]
"""

import argparse
import json
import re
import time
from pathlib import Path
import requests
from google_helpers import read_sheet, list_drive_folder, upload_to_drive

# TikTok download API (via tdown.app backend)
TIKTOK_API = "https://tiktok-void-backend.onrender.com/api/download"
HEADERS = {
    'Content-Type': 'application/json',
    'Origin': 'https://www.tdown.app',
    'Referer': 'https://www.tdown.app/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
}

TMP_DIR = Path(__file__).parent.parent / '.tmp'


def normalize_name(name):
    """Normalize player name for matching (lowercase, strip extra chars)."""
    # Remove parenthetical suffixes like (1), (2)
    name = re.sub(r'\(\d+\)$', '', name).strip()
    return name.lower().strip()


def extract_tiktok_urls(row):
    """Extract all TikTok URLs from a row (columns 2+)."""
    urls = []
    for cell in row[1:]:  # Skip first column (player name)
        if cell and 'tiktok.com' in cell.lower():
            urls.append(cell.strip())
    return urls


def get_tiktok_download_url(tiktok_url):
    """Get the no-watermark download URL for a TikTok video."""
    try:
        # Clean URL - extract just the essential part
        clean_url = tiktok_url.split('?')[0] if '?' in tiktok_url else tiktok_url

        response = requests.post(
            TIKTOK_API,
            headers=HEADERS,
            json={'url': clean_url},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        if data.get('success') and data.get('data', {}).get('success'):
            return {
                'download_url': data['data'].get('no_watermark_download_url') or data['data'].get('downloadUrl'),
                'video_id': data['data'].get('id'),
                'title': data['data'].get('title', ''),
                'author': data['data'].get('author', '')
            }
        else:
            print(f"  API returned unsuccessful for: {tiktok_url}")
            return None

    except requests.RequestException as e:
        print(f"  Error fetching download URL: {e}")
        return None


def download_video(download_url, video_id, output_dir):
    """Download video to local file."""
    output_path = output_dir / f"{video_id}.mp4"

    try:
        response = requests.get(download_url, stream=True, timeout=120)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return output_path
    except requests.RequestException as e:
        print(f"  Error downloading video: {e}")
        return None


def build_folder_map(folder_id):
    """Build a mapping of normalized player names to folder IDs."""
    folders = list_drive_folder(folder_id)
    folder_map = {}

    for f in folders:
        if f['mimeType'] == 'application/vnd.google-apps.folder':
            normalized = normalize_name(f['name'])
            folder_map[normalized] = {
                'id': f['id'],
                'name': f['name']
            }

    return folder_map


def find_matching_folder(player_name, folder_map):
    """Find the best matching folder for a player name."""
    normalized = normalize_name(player_name)

    # Exact match
    if normalized in folder_map:
        return folder_map[normalized]

    # Partial match (player name contains folder name or vice versa)
    for folder_norm, folder_info in folder_map.items():
        if normalized in folder_norm or folder_norm in normalized:
            return folder_info

    return None


def main():
    parser = argparse.ArgumentParser(description='Download TikTok videos to Google Drive')
    parser.add_argument('--sheet-id', required=True, help='Google Sheet ID')
    parser.add_argument('--folder-id', required=True, help='Google Drive folder ID')
    parser.add_argument('--dry-run', action='store_true', help='Print actions without executing')
    parser.add_argument('--delay', type=float, default=2.0, help='Delay between downloads (seconds)')

    args = parser.parse_args()

    # Ensure tmp directory exists
    TMP_DIR.mkdir(exist_ok=True)

    # Read sheet data
    print("Reading sheet data...")
    rows = read_sheet(args.sheet_id)

    # Build folder map
    print("Building folder map...")
    folder_map = build_folder_map(args.folder_id)
    print(f"Found {len(folder_map)} player folders")

    # Process each row
    stats = {'downloaded': 0, 'uploaded': 0, 'skipped': 0, 'errors': 0}

    for row in rows:
        if not row:
            continue

        player_name = row[0]
        tiktok_urls = extract_tiktok_urls(row)

        if not tiktok_urls:
            continue

        print(f"\n{'='*50}")
        print(f"Player: {player_name}")
        print(f"TikTok URLs: {len(tiktok_urls)}")

        # Find matching folder
        folder_info = find_matching_folder(player_name, folder_map)
        if not folder_info:
            print(f"  WARNING: No matching folder found for '{player_name}'")
            stats['skipped'] += len(tiktok_urls)
            continue

        print(f"  Folder: {folder_info['name']} ({folder_info['id']})")

        for url in tiktok_urls:
            print(f"\n  Processing: {url[:60]}...")

            if args.dry_run:
                print(f"    [DRY RUN] Would download and upload to {folder_info['name']}")
                continue

            # Get download URL
            video_info = get_tiktok_download_url(url)
            if not video_info:
                stats['errors'] += 1
                continue

            print(f"    Video ID: {video_info['video_id']}")

            # Download video
            local_path = download_video(
                video_info['download_url'],
                video_info['video_id'],
                TMP_DIR
            )

            if not local_path:
                stats['errors'] += 1
                continue

            print(f"    Downloaded: {local_path.name} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")
            stats['downloaded'] += 1

            # Upload to Drive
            try:
                result = upload_to_drive(
                    str(local_path),
                    folder_info['id'],
                    f"{video_info['video_id']}.mp4"
                )
                print(f"    Uploaded: {result.get('name')}")
                stats['uploaded'] += 1
            except Exception as e:
                print(f"    Upload error: {e}")
                stats['errors'] += 1

            # Clean up local file
            try:
                local_path.unlink()
            except:
                pass

            # Rate limiting
            time.sleep(args.delay)

    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print(f"  Downloaded: {stats['downloaded']}")
    print(f"  Uploaded: {stats['uploaded']}")
    print(f"  Skipped: {stats['skipped']}")
    print(f"  Errors: {stats['errors']}")


if __name__ == '__main__':
    main()
