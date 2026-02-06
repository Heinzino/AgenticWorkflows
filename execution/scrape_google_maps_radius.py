#!/usr/bin/env python3
"""
Google Maps Lead Scraping (Radius-Based)
Uses Apify API to scrape businesses within a radius, handling pagination via grid cells.
"""

import argparse
import json
import math
import os
import sys
import time
import platform
from datetime import datetime
from typing import List, Dict, Set, Tuple
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
APIFY_API_KEY = os.getenv("APIFY_API_KEY")
APIFY_ACTOR_ID = "compass~crawler-google-places"
EARTH_RADIUS_KM = 6371
GRID_CELL_SIZE_KM = 2  # 2km x 2km cells to avoid hitting API limits


class GoogleMapsRadiusScraper:
    def __init__(self, lat: float, lon: float, radius_km: int, business_types: List[str]):
        self.center_lat = lat
        self.center_lon = lon
        self.radius_km = radius_km
        self.business_types = business_types if business_types and business_types != ["all"] else []
        self.results: Dict[str, Dict] = {}  # place_id -> business data
        self.apify_url = f"https://api.apify.com/v2/acts/{APIFY_ACTOR_ID}/run-sync-get-dataset-items"

        if not APIFY_API_KEY:
            raise ValueError("APIFY_API_KEY not found in .env file")

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers."""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return EARTH_RADIUS_KM * c

    def generate_grid_cells(self) -> List[Tuple[float, float, float, float]]:
        """
        Generate grid cells (bounding boxes) that cover the radius.
        Returns list of (min_lat, min_lon, max_lat, max_lon) tuples.
        """
        # Calculate degrees per km at this latitude
        lat_deg_per_km = 1 / 111.32
        lon_deg_per_km = 1 / (111.32 * math.cos(math.radians(self.center_lat)))

        # Calculate grid boundaries
        lat_cells = int(math.ceil(self.radius_km * 2 / GRID_CELL_SIZE_KM))
        lon_cells = int(math.ceil(self.radius_km * 2 / GRID_CELL_SIZE_KM))

        cells = []
        for i in range(-lat_cells, lat_cells + 1):
            for j in range(-lon_cells, lon_cells + 1):
                # Calculate cell corners
                min_lat = self.center_lat + (i * GRID_CELL_SIZE_KM * lat_deg_per_km)
                max_lat = self.center_lat + ((i + 1) * GRID_CELL_SIZE_KM * lat_deg_per_km)
                min_lon = self.center_lon + (j * GRID_CELL_SIZE_KM * lon_deg_per_km)
                max_lon = self.center_lon + ((j + 1) * GRID_CELL_SIZE_KM * lon_deg_per_km)

                # Check if cell center is within radius
                cell_center_lat = (min_lat + max_lat) / 2
                cell_center_lon = (min_lon + max_lon) / 2
                distance = self.haversine_distance(
                    self.center_lat, self.center_lon,
                    cell_center_lat, cell_center_lon
                )

                if distance <= self.radius_km:
                    cells.append((min_lat, min_lon, max_lat, max_lon))

        print(f"Generated {len(cells)} grid cells to cover {self.radius_km}km radius")
        return cells

    def create_polygon_coords(self, min_lat: float, min_lon: float,
                            max_lat: float, max_lon: float) -> List[List[float]]:
        """Create polygon coordinates for Apify API (clockwise from top-right)."""
        return [
            [max_lon, max_lat],  # Top-right
            [max_lon, min_lat],  # Bottom-right
            [min_lon, min_lat],  # Bottom-left
            [min_lon, max_lat],  # Top-left
            [max_lon, max_lat]   # Close polygon
        ]

    def scrape_cell(self, cell_coords: Tuple[float, float, float, float],
                   cell_num: int, total_cells: int) -> int:
        """Scrape a single grid cell and add results to self.results."""
        min_lat, min_lon, max_lat, max_lon = cell_coords
        polygon = self.create_polygon_coords(min_lat, min_lon, max_lat, max_lon)

        payload = {
            "allPlacesNoSearchAction": "all_places_no_search_ocr",
            "customGeolocation": {
                "type": "Polygon",
                "coordinates": [polygon]
            },
            "includeWebResults": False,
            "language": "en",
            "maxCrawledPlacesPerSearch": 500,
            "maxImages": 0,
            "scrapeContacts": False,
            "scrapeDirectories": False,
            "scrapeImageAuthors": False,
            "scrapePlaceDetailPage": False,
            "scrapeReviewsPersonalData": False,
            "scrapeTableReservationProvider": False,
            "skipClosedPlaces": False
        }

        headers = {
            "Content-Type": "application/json"
        }

        params = {
            "token": APIFY_API_KEY
        }

        print(f"[{cell_num}/{total_cells}] Scraping cell: lat {min_lat:.4f} to {max_lat:.4f}, lon {min_lon:.4f} to {max_lon:.4f}")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.apify_url,
                    json=payload,
                    headers=headers,
                    params=params,
                    timeout=120
                )

                if response.status_code == 429:
                    print(f"  Rate limit hit, waiting 60 seconds...")
                    time.sleep(60)
                    continue

                response.raise_for_status()
                results = response.json()

                # Process results
                new_count = 0
                for place in results:
                    place_id = place.get("placeId")
                    if not place_id:
                        continue

                    # Check if within radius
                    place_lat = place.get("location", {}).get("lat")
                    place_lon = place.get("location", {}).get("lng")
                    if place_lat and place_lon:
                        distance = self.haversine_distance(
                            self.center_lat, self.center_lon,
                            place_lat, place_lon
                        )
                        if distance > self.radius_km:
                            continue

                    # Filter by business type if specified
                    if self.business_types:
                        categories = place.get("categories", [])
                        if not any(bt.lower() in [c.lower() for c in categories] for bt in self.business_types):
                            continue

                    # Add to results if new
                    if place_id not in self.results:
                        self.results[place_id] = {
                            "business_name": place.get("title", ""),
                            "address": place.get("address", ""),
                            "phone": place.get("phoneUnformatted", ""),
                            "website": place.get("website", ""),
                            "rating": place.get("totalScore", 0),
                            "total_reviews": place.get("reviewsCount", 0),
                            "categories": ", ".join(place.get("categories", [])),
                            "latitude": place_lat,
                            "longitude": place_lon,
                            "place_id": place_id,
                            "google_maps_url": place.get("url", "")
                        }
                        new_count += 1

                print(f"  Found {len(results)} results, {new_count} new unique businesses (total: {len(self.results)})")
                return new_count

            except requests.exceptions.Timeout:
                print(f"  Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(5)
            except requests.exceptions.RequestException as e:
                print(f"  Error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)

        print(f"  Failed after {max_retries} attempts, skipping cell")
        return 0

    def scrape(self) -> Dict[str, Dict]:
        """Execute the full scraping process."""
        print(f"\n{'='*60}")
        print(f"Starting Google Maps scrape:")
        print(f"  Center: {self.center_lat}, {self.center_lon}")
        print(f"  Radius: {self.radius_km} km")
        print(f"  Business types: {self.business_types if self.business_types else 'All'}")
        print(f"{'='*60}\n")

        cells = self.generate_grid_cells()

        for i, cell in enumerate(cells, 1):
            self.scrape_cell(cell, i, len(cells))
            # Small delay between cells to be nice to the API
            if i < len(cells):
                time.sleep(2)

        print(f"\n{'='*60}")
        print(f"Scraping complete!")
        print(f"Total unique businesses found: {len(self.results)}")
        print(f"{'='*60}\n")

        return self.results


def save_to_json(data: Dict, output_path: str):
    """Save results to JSON file."""
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(list(data.values()), f, indent=2, ensure_ascii=False)
    print(f"Saved intermediate data to: {output_path}")


def save_to_csv(data: Dict, output_path: str):
    """Save results to CSV file."""
    import csv

    if not data:
        print("No data to save")
        return

    fieldnames = list(next(iter(data.values())).keys())

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data.values())

    print(f"Saved CSV to: {output_path}")


def play_completion_beep():
    """Play a system beep to notify completion."""
    try:
        if platform.system() == "Windows":
            import winsound
            # Play three beeps
            for _ in range(3):
                winsound.Beep(1000, 200)  # 1000 Hz for 200ms
                time.sleep(0.1)
        else:
            # Unix-like systems
            print('\a' * 3)  # Terminal bell
    except Exception as e:
        print(f"Could not play beep: {e}")


def main():
    parser = argparse.ArgumentParser(description='Scrape Google Maps businesses within a radius')
    parser.add_argument('--lat', type=float, required=True, help='Center latitude')
    parser.add_argument('--lon', type=float, required=True, help='Center longitude')
    parser.add_argument('--radius', type=int, required=True, help='Radius in kilometers')
    parser.add_argument('--business-types', type=str, default='all',
                       help='Comma-separated business types or "all" (default: all)')
    parser.add_argument('--output-format', type=str, choices=['csv', 'sheet', 'json'],
                       default='sheet', help='Output format (default: sheet)')

    args = parser.parse_args()

    # Validate inputs
    if not -90 <= args.lat <= 90:
        print("Error: Latitude must be between -90 and 90")
        sys.exit(1)

    if not -180 <= args.lon <= 180:
        print("Error: Longitude must be between -180 and 180")
        sys.exit(1)

    if args.radius <= 0:
        print("Error: Radius must be greater than 0")
        sys.exit(1)

    # Parse business types
    business_types = [] if args.business_types == 'all' else [
        bt.strip() for bt in args.business_types.split(',')
    ]

    # Create .tmp directory if it doesn't exist
    os.makedirs('.tmp', exist_ok=True)

    # Initialize scraper and run
    scraper = GoogleMapsRadiusScraper(args.lat, args.lon, args.radius, business_types)
    results = scraper.scrape()

    # Save intermediate JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = f".tmp/google_maps_leads_{timestamp}.json"
    save_to_json(results, json_path)

    # Handle output format
    if args.output_format == 'csv':
        csv_path = f".tmp/google_maps_leads_{timestamp}.csv"
        save_to_csv(results, csv_path)
        print(f"\n[SUCCESS] Final output: {csv_path}")

    elif args.output_format == 'sheet':
        print("\nUploading to Google Sheets...")
        # This would call upload_to_sheet.py if it exists
        # For now, save CSV and tell user to manually upload
        csv_path = f".tmp/google_maps_leads_{timestamp}.csv"
        save_to_csv(results, csv_path)
        print(f"CSV ready for upload: {csv_path}")
        print("Google Sheets integration not yet implemented - please upload CSV manually")

    elif args.output_format == 'json':
        print(f"\n[SUCCESS] Final output: {json_path}")

    # Play completion beep
    print("\n" + "="*60)
    print("TASK COMPLETE!")
    print("="*60)
    play_completion_beep()


if __name__ == "__main__":
    main()
