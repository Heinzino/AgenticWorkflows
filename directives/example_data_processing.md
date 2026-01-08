# Data Processing Directive

## Goal
Process raw data, apply transformations, and output structured results.

## Inputs
- `input_file` (string, required): Path to input data file (CSV, JSON, or Sheet URL)
- `transformations` (list, required): List of transformation operations to apply
- `output_destination` (string, optional): Where to save results (file path or "sheet")

## Tools/Scripts
- **Primary**: `execution/process_data.py`
- **Sheet integration**: `execution/read_sheet.py`, `execution/update_sheet.py`

## Process
1. Read input data using appropriate script:
   - If file: Load directly from path
   - If Sheet URL: Use `execution/read_sheet.py` to download to `.tmp/`
2. Execute transformations in order:
   ```bash
   python execution/process_data.py --input <path> --transformations <operations> --output <destination>
   ```
3. Save processed data:
   - Intermediate: `.tmp/processed_<timestamp>.json`
   - Final: Google Sheet or specified file path

## Outputs
- **Intermediate**: `.tmp/processed_<timestamp>.json`
- **Deliverable**: Google Sheet URL or processed file path

## Available Transformations
- `deduplicate`: Remove duplicate rows
- `filter`: Filter rows by condition
- `aggregate`: Group and summarize data
- `enrich`: Add calculated fields
- `validate`: Check data quality
- `normalize`: Standardize formats

## Edge Cases & Learnings

### Large Files
- Files >100MB should be processed in chunks
- Use `--chunk-size <rows>` parameter (default: 10000)

### Data Quality Issues
- Missing values: Script handles with configurable strategy (drop, fill, interpolate)
- Invalid formats: Log errors to `.tmp/validation_errors.log`
- Type mismatches: Auto-convert where possible, flag otherwise

### Memory Constraints
- For very large datasets, use `--streaming` mode
- Processes data in batches without loading everything into memory

## Error Handling
- **File not found**: Verify path and check read permissions
- **Invalid transformation**: List valid operations and ask for clarification
- **Sheet quota exceeded**: Wait and retry, or switch to local processing

## Testing
Test with sample data:
```bash
python execution/process_data.py --input .tmp/sample.csv --transformations deduplicate,validate --output sheet
```

## Last Updated
2026-01-07 - Initial creation
