#!/usr/bin/env python3
"""
Process data with various transformations.

Usage:
    python process_data.py --input data.csv --transformations deduplicate,validate --output sheet
"""

import argparse
import json
import csv
from datetime import datetime
from pathlib import Path
import pandas as pd


class DataProcessor:
    """Handle data processing transformations."""

    def __init__(self, data):
        """Initialize with data (DataFrame)."""
        self.df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data)
        self.errors = []

    def deduplicate(self):
        """Remove duplicate rows."""
        before = len(self.df)
        self.df = self.df.drop_duplicates()
        after = len(self.df)
        print(f"Removed {before - after} duplicate rows")
        return self

    def filter_rows(self, condition):
        """Filter rows by condition."""
        # Example: condition = "age > 18"
        try:
            self.df = self.df.query(condition)
            print(f"Filtered to {len(self.df)} rows")
        except Exception as e:
            print(f"Filter error: {e}")
            self.errors.append(f"Filter failed: {e}")
        return self

    def aggregate(self, group_by, agg_func):
        """Group and aggregate data."""
        try:
            self.df = self.df.groupby(group_by).agg(agg_func).reset_index()
            print(f"Aggregated by {group_by}")
        except Exception as e:
            print(f"Aggregation error: {e}")
            self.errors.append(f"Aggregation failed: {e}")
        return self

    def enrich(self, new_column, expression):
        """Add calculated fields."""
        try:
            self.df[new_column] = self.df.eval(expression)
            print(f"Added column: {new_column}")
        except Exception as e:
            print(f"Enrichment error: {e}")
            self.errors.append(f"Enrichment failed: {e}")
        return self

    def validate(self):
        """Check data quality."""
        issues = []

        # Check for missing values
        missing = self.df.isnull().sum()
        if missing.any():
            issues.append(f"Missing values: {missing[missing > 0].to_dict()}")

        # Check for duplicates
        duplicates = self.df.duplicated().sum()
        if duplicates > 0:
            issues.append(f"Duplicate rows: {duplicates}")

        # Log validation results
        if issues:
            print("Validation issues found:")
            for issue in issues:
                print(f"  - {issue}")
            self.errors.extend(issues)
        else:
            print("Validation passed!")

        return self

    def normalize(self):
        """Standardize formats."""
        # Convert string columns to consistent case
        for col in self.df.select_dtypes(include=['object']).columns:
            self.df[col] = self.df[col].str.strip()

        # Standardize date formats
        for col in self.df.columns:
            if 'date' in col.lower():
                try:
                    self.df[col] = pd.to_datetime(self.df[col])
                except:
                    pass

        print("Data normalized")
        return self

    def get_data(self):
        """Return processed DataFrame."""
        return self.df


def load_data(input_path):
    """Load data from file or sheet."""
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Determine format and load
    if path.suffix == '.csv':
        return pd.read_csv(path)
    elif path.suffix == '.json':
        return pd.read_json(path)
    elif path.suffix in ['.xlsx', '.xls']:
        return pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")


def save_output(df, output_format, output_dir='.tmp'):
    """Save processed data."""
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    if output_format == 'json':
        output_path = Path(output_dir) / f'processed_{timestamp}.json'
        df.to_json(output_path, orient='records', indent=2)
        print(f"Saved to: {output_path}")
        return str(output_path)

    elif output_format == 'csv':
        output_path = Path(output_dir) / f'processed_{timestamp}.csv'
        df.to_csv(output_path, index=False)
        print(f"Saved to: {output_path}")
        return str(output_path)

    elif output_format == 'sheet':
        # Save intermediate JSON first
        json_path = save_output(df, 'json', output_dir)
        print(f"Use: python execution/update_sheet.py --input {json_path}")
        return json_path

    else:
        raise ValueError(f"Unsupported format: {output_format}")


def main():
    parser = argparse.ArgumentParser(description='Process data with transformations')
    parser.add_argument('--input', required=True, help='Input file path')
    parser.add_argument('--transformations', required=True,
                       help='Comma-separated transformations')
    parser.add_argument('--output-format', default='json',
                       choices=['json', 'csv', 'sheet'],
                       help='Output format')
    parser.add_argument('--chunk-size', type=int, default=10000,
                       help='Chunk size for large files')

    args = parser.parse_args()

    try:
        # Load data
        print(f"Loading data from: {args.input}")
        data = load_data(args.input)
        print(f"Loaded {len(data)} rows")

        # Process transformations
        processor = DataProcessor(data)
        transformations = [t.strip() for t in args.transformations.split(',')]

        for transform in transformations:
            print(f"Applying: {transform}")
            if hasattr(processor, transform):
                getattr(processor, transform)()
            else:
                print(f"Warning: Unknown transformation '{transform}'")
                print("Available: deduplicate, filter, aggregate, enrich, validate, normalize")

        # Save output
        result = processor.get_data()
        output_path = save_output(result, args.output_format)
        print(f"Success! Processed {len(result)} rows -> {output_path}")

        # Log errors if any
        if processor.errors:
            error_log = Path('.tmp') / 'validation_errors.log'
            with open(error_log, 'a') as f:
                f.write(f"\n=== {datetime.now().isoformat()} ===\n")
                for error in processor.errors:
                    f.write(f"{error}\n")
            print(f"Errors logged to: {error_log}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
