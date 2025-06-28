"""
CLI tool for TMX to CSV conversion.
"""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from app.database.corpus_migrator import TMXParser


def main():
    """CLI entry point for TMX to CSV conversion."""
    parser = argparse.ArgumentParser(description='Convert TMX files to CSV format')
    parser.add_argument('tmx_file', help='Input TMX file')
    parser.add_argument('csv_file', help='Output CSV file')
    parser.add_argument('--source-lang', default='en', help='Source language code (default: en)')
    parser.add_argument('--target-lang', default='pl', help='Target language code (default: pl)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    tmx_path = Path(args.tmx_file)
    csv_path = Path(args.csv_file)
    
    if not tmx_path.exists():
        print(f"Error: TMX file {tmx_path} does not exist")
        return 1
    
    if not tmx_path.suffix.lower() == '.tmx':
        print(f"Error: Input file must be a TMX file")
        return 1
    
    try:
        print(f"Converting {tmx_path} to {csv_path}")
        print(f"Source language: {args.source_lang}")
        print(f"Target language: {args.target_lang}")
        
        records_converted = TMXParser.parse_tmx_to_csv(
            tmx_path, 
            csv_path, 
            args.source_lang, 
            args.target_lang
        )
        
        print(f"\\nConversion completed successfully!")
        print(f"Records converted: {records_converted:,}")
        print(f"Output file: {csv_path}")
        
        return 0
        
    except Exception as e:
        print(f"Conversion failed: {e}")
        logging.exception("Conversion error")
        return 1


if __name__ == '__main__':
    exit(main())
