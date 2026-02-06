# Google Maps Lead Scraping (Radius-Based)

## Goal
Scrape all businesses within a specified radius using Google Maps data via Apify API. Handles pagination and large result sets by breaking area into grid cells.

## Inputs
- `latitude` (float, required): Center point latitude (e.g., 51.0447 for Calgary)
- `longitude` (float, required): Center point longitude (e.g., -114.0719 for Calgary)
- `radius_km` (int, required): Radius in kilometers (e.g., 16)
- `business_types` (list, optional): Specific business categories to filter. Use empty list or "all" for all businesses.
- `output_format` (string, optional): "csv" or "sheet". Defaults to "sheet".

## Tools/Scripts
- **Primary**: `execution/scrape_google_maps_radius.py`
- **API**: Apify Google Places Crawler (compass~crawler-google-places)

## Process
1. Validate inputs (lat/long in valid range, radius > 0)
2. Calculate grid cells to cover the radius area (max 2km per cell to avoid API limits)
3. For each grid cell:
   - Make API request to Apify with polygon coordinates
   - Handle pagination (Google Places returns max ~200 results per search)
   - Deduplicate results across grid cells (same business may appear in multiple cells)
4. Save intermediate results to `.tmp/google_maps_leads_<timestamp>.json`
5. If output_format is "sheet", upload to Google Sheets
6. Return deliverable location (Google Sheet URL or CSV file path)

## Command
```bash
python execution/scrape_google_maps_radius.py --lat 51.0447 --lon -114.0719 --radius 16 --business-types all --output-format sheet
```

## Outputs
- **Intermediate**: `.tmp/google_maps_leads_<timestamp>.json` (raw API responses)
- **Deliverable**: Google Sheet with columns:
  - Business Name
  - Address
  - Phone
  - Website
  - Rating
  - Total Reviews
  - Categories
  - Latitude
  - Longitude
  - Place ID
  - Google Maps URL

## Edge Cases & Learnings

### API Rate Limits
- Apify has rate limits on the free tier
- If you hit limits, the script will wait and retry with exponential backoff
- Large radii (>20km) may take 10-30 minutes to complete

### Grid Cell Strategy
- Each grid cell is ~2km x 2km
- 16km radius = ~201 grid cells
- This ensures we don't hit Google's ~200 result limit per search area
- Overlap between cells ensures no businesses are missed

### Deduplication
- Same business can appear in multiple grid cells
- Script deduplicates using `place_id` (Google's unique identifier)
- Final count should match actual unique businesses

### Missing Data
- Some businesses don't have phone numbers or websites
- These fields will be empty strings in the output
- Rating/reviews will be 0 if not available

### Business Types Filter
- Google uses specific category names (e.g., "restaurant", "plumber", "hair_salon")
- When filtering, script matches against Google's category taxonomy
- "all" or empty list means no filtering

## Error Handling
- **Invalid coordinates**: Fail fast with clear error message
- **API timeout**: Retry up to 3 times with 5 second delay
- **Rate limit (429)**: Wait 60 seconds and retry
- **Invalid API response**: Log the cell coordinates and continue with next cell
- **Partial failures**: Save progress after each grid cell to avoid losing data

## Testing
Test with a small radius first (1-2 km) to verify setup:
```bash
python execution/scrape_google_maps_radius.py --lat 51.0447 --lon -114.0719 --radius 2 --business-types all --output-format csv
```

Expected: 100-500 results depending on business density.

## Cost Estimate
- Apify pricing: ~$0.01-0.05 per 1000 results (varies by plan)
- 16km radius in urban area: estimate 2,000-10,000 businesses
- Approximate cost: $0.02-0.50 per full scrape

## Last Updated
2026-01-11 - Initial creation for Calgary 16km radius scraping
