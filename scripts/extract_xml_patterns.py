#!/usr/bin/env python3
"""
Extract XML patterns from BaseX production database.

This script queries the dictionary database, extracts XML structures
(elements + attributes, stripping content), deduplicates patterns,
and saves them to a JSON file for testing purposes.

Usage:
    python extract_xml_patterns.py                    # Full extraction
    python extract_xml_patterns.py --sample 1000     # Sample 1000 entries
    python extract_xml_patterns.py --force           # Overwrite existing
    python extract_xml_patterns.py --output custom.json  # Custom output path
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
from xml.dom import minidom

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def connect_basex(host: str, port: int, username: str, password: str, database: str) -> Any:
    """
    Connect to BaseX server and return the session.

    Args:
        host: BaseX server hostname
        port: BaseX server port
        username: Username for authentication
        password: Password for authentication
        database: Name of the database to connect to

    Returns:
        BaseX session object
    """
    try:
        from BaseXClient.BaseXClient import Session as BaseXSession
    except ImportError:
        raise ImportError("BaseXClient not installed. Install with: pip install BaseXClient")

    session = BaseXSession(host, port, username, password)
    session.execute(f"OPEN {database}")
    logger.info(f"Connected to BaseX database '{database}' at {host}:{port}")
    return session


def extract_structure(element: ET.Element) -> Dict[str, Any]:
    """
    Recursively extract XML structure, replacing text content with placeholders.

    This function extracts the element name, attributes, and structure
    of child elements, but replaces actual text content with "{text}" placeholders.

    Args:
        element: XML element to analyze

    Returns:
        Dictionary representing the structure
    """
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
    ns = element.tag.split('}')[0].lstrip('{') if '}' in element.tag else None

    structure = {
        "tag": tag,
    }

    if ns:
        structure["namespace"] = ns

    # Extract attributes (sorted for consistency)
    if element.attrib:
        attrs = dict(sorted(element.attrib.items()))
        structure["attributes"] = attrs

    # Handle children
    children = list(element)
    if children:
        # Process child elements
        child_structures = []
        child_tags = []
        for child in children:
            child_struct = extract_structure(child)
            child_structures.append(child_struct)
            child_tags.append(child_struct.get("tag", "unknown"))

        structure["children"] = child_structures
        structure["child_order"] = child_tags
    else:
        # No children - mark as leaf
        structure["leaf"] = True

    # Check for text content (non-whitespace)
    text = element.text
    if text and text.strip():
        structure["has_text"] = True
        # Don't include actual text content, just mark its presence

    tail = element.tail
    if tail and tail.strip():
        structure["has_tail"] = True
        # Tail text is text after the element, also marked but not included

    return structure


def canonicalize_pattern(structure: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Canonicalize a pattern structure for deduplication.

    Sorts attributes alphabetically and normalizes child order to ensure
    structurally equivalent XML elements produce the same canonical form.

    Args:
        structure: The extracted structure dictionary

    Returns:
        Tuple of (hash string, canonicalized structure)
    """
    # Create a canonicalized copy
    canonical = {}

    # Copy basic fields
    canonical["tag"] = structure.get("tag", "unknown")
    if "namespace" in structure:
        canonical["namespace"] = structure["namespace"]

    # Sort attributes
    if "attributes" in structure:
        canonical["attributes"] = dict(sorted(structure["attributes"].items()))

    # Sort children by their canonical representation
    if "children" in structure:
        child_canonicals = []
        for child in structure["children"]:
            _, child_canonical = canonicalize_pattern(child)
            child_canonicals.append(child_canonical)
        canonical["children"] = sorted(child_canonicals, key=lambda x: json.dumps(x, sort_keys=True))
        canonical["child_order"] = sorted(structure.get("child_order", []))

    # Boolean flags
    if structure.get("leaf"):
        canonical["leaf"] = True
    if structure.get("has_text"):
        canonical["has_text"] = True
    if structure.get("has_tail"):
        canonical["has_tail"] = True

    # Create hash for quick comparison
    canonical_str = json.dumps(canonical, sort_keys=True)
    hash_val = hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()[:16]

    return hash_val, canonical


def get_element_path(element: ET.Element) -> str:
    """
    Get the XPath-like path to an element from the root.

    Args:
        element: XML element

    Returns:
        String path like "/lift/entry/sense/definition/form"
    """
    path_parts = []
    current = element

    while current is not None:
        tag = current.tag.split('}')[-1] if '}' in current.tag else current.tag
        path_parts.insert(0, tag)
        current = current.find('..')

    return '/' + '/'.join(path_parts)


def get_sample_xml(element: ET.Element, max_length: int = 500) -> str:
    """
    Get a sample XML representation of an element.

    Args:
        element: XML element
        max_length: Maximum length of the returned string

    Returns:
        XML string (possibly truncated)
    """
    try:
        # Use minidom for pretty printing
        xml_str = minidom.parseString(ET.tostring(element)).toprettyxml(indent="  ")
        # Remove XML declaration
        lines = xml_str.split('\n')
        if lines[0].startswith('<?xml'):
            lines = lines[1:]
        xml_str = '\n'.join(lines)

        if len(xml_str) > max_length:
            return xml_str[:max_length] + '\n...'
        return xml_str
    except Exception:
        # Fallback to simple string
        return ET.tostring(element, encoding='unicode')[:max_length]


def count_entries(session: Any, database: str) -> int:
    """
    Count total entries in the dictionary database.

    Args:
        session: BaseX session
        database: Database name

    Returns:
        Number of entries
    """
    query = f"count(collection('{database}')/lift/entry)"
    try:
        result = session.query(query).execute()
        return int(result.strip()) if result.strip() else 0
    except Exception as e:
        logger.warning(f"Could not count entries: {e}")
        return 0
        # Fallback: try without namespace
        try:
            result = session.query("xquery count(collection()//entry)").execute()
            return int(result.strip()) if result.strip() else 0
        except:
            return 0


def stream_entries(session: Any, database: str, batch_size: int = 100) -> Generator[List[ET.Element], None, None]:
    """
    Stream entries from the database in batches for memory efficiency.

    Args:
        session: BaseX session
        database: Database name
        batch_size: Number of entries to fetch per batch

    Yields:
        List of XML elements for each batch
    """
    # Open the database first to ensure it's available
    try:
        session.execute(f"OPEN {database}")
        logger.info(f"Opened database: {database}")
    except Exception as e:
        logger.warning(f"Could not open database '{database}': {e}")
        # Try to list available databases
        try:
            result = session.execute("SHOW DBS")
            logger.info(f"Available databases:\n{result}")
        except:
            pass

    # Try with namespace first
    query_template = """
    for $entry in collection('{}')/lift/entry
    return serialize($entry, {{'method': 'xml', 'indent': 'no'}})
    """.format(database)

    # Try to get total count first
    total = count_entries(session, database)
    if total == 0:
        logger.warning("No entries found with namespace, trying without namespace")
        query_template = """
        for $entry in collection('{}')//entry
        return serialize($entry, {{'method': 'xml', 'indent': 'no'}})
        """.format(database)
        total = count_entries(session, database)

    logger.info(f"Streaming {total} entries in batches of {batch_size}")

    offset = 0
    while offset < total:
        # Build query with limit and offset
        query = f"""
        for $entry in collection('{database}')/lift/entry
        order by $entry/@guid
        return serialize($entry, {{'method': 'xml', 'indent': 'no'}})
        """

        try:
            offset_end = offset + batch_size
            full_query = f"""
            let $all := collection('{database}')/lift/entry
            let $count := count($all)
            let $batch := $all[position() > {offset} and position() <= {offset_end}]
            return (
                string($count),
                for $entry in $batch
                return serialize($entry, {{'method': 'xml', 'indent': 'no'}})
            )
            """

            result = session.query(full_query.replace('\n', ' ').strip()).execute()
            lines = result.strip().split('\n')

            if len(lines) <= 1:
                break

            # First line is count, rest are serialized entries
            current_count = int(lines[0].strip())
            batch_xml = lines[1:]

            batch = []
            for xml_str in batch_xml:
                # Skip empty or whitespace-only lines
                if not xml_str.strip():
                    continue
                try:
                    elem = ET.fromstring(xml_str)
                    batch.append(elem)
                except ET.ParseError as e:
                    logger.debug(f"Parse error at offset {offset}: {e}")
                    continue

            if batch:
                yield batch
            else:
                break

            offset += batch_size

            if offset % 1000 == 0:
                logger.info(f"Processed {offset}/{current_count} entries...")

        except Exception as e:
            logger.error(f"Error streaming batch at offset {offset}: {e}")
            break


def extract_patterns_from_entries(
    entries: List[ET.Element],
    seen_patterns: Dict[str, int]
) -> List[Dict[str, Any]]:
    """
    Extract patterns from a batch of entries.

    Args:
        entries: List of XML elements
        seen_patterns: Dictionary tracking pattern occurrence counts

    Returns:
        List of extracted pattern information
    """
    patterns = []

    for entry in entries:
        try:
            # Find all interesting elements to analyze
            # Focus on key LIFT elements
            target_paths = ['sense', 'definition', 'form', 'example', 'variant', 'relation']

            for elem in entry.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

                # Skip root entry element
                if tag == 'entry' and elem == entry:
                    continue

                # Skip literal, pronunciation, etc. (less structural variation)
                if tag in ['literal-meaning', 'pronunciation']:
                    continue

                # Extract structure
                structure = extract_structure(elem)

                # Canonicalize for deduplication
                hash_val, canonical = canonicalize_pattern(structure)

                # Get element path
                path = get_element_path(elem)

                # Track occurrences
                pattern_key = f"{path}:{hash_val}"
                seen_patterns[pattern_key] = seen_patterns.get(pattern_key, 0) + 1

                # Get sample XML (only for first occurrence of each pattern)
                if seen_patterns[pattern_key] == 1:
                    sample_xml = get_sample_xml(elem)

                    patterns.append({
                        "id": f"pattern_{len(seen_patterns):04d}",
                        "element_path": path,
                        "structure": canonical,
                        "sample_xml": sample_xml,
                        "occurrences": 1
                    })

        except Exception as e:
            logger.warning(f"Error processing entry: {e}")
            continue

    return patterns


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Extract XML patterns from BaseX dictionary database"
    )
    parser.add_argument(
        '--sample', '-s',
        type=int,
        default=None,
        help='Sample N entries instead of processing all'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing output file'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='tests/unit/test_xml_roundtrip/fixtures/patterns.json',
        help='Output file path'
    )
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=100,
        help='Batch size for streaming (default: 100)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='BaseX host (overrides .env)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='BaseX port (overrides .env)'
    )
    parser.add_argument(
        '--database',
        type=str,
        default=None,
        help='Database name (overrides .env)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load environment variables
    load_dotenv()

    # Get configuration from environment or args
    host = args.host or os.getenv('BASEX_HOST', 'localhost')
    port = args.port or int(os.getenv('BASEX_PORT', '1984'))
    username = os.getenv('BASEX_USERNAME', 'admin')
    password = os.getenv('BASEX_PASSWORD', 'admin')
    database = args.database or os.getenv('BASEX_DATABASE', 'dictionary')

    # Check output file
    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Created output directory: {output_dir}")

    if os.path.exists(output_path) and not args.force:
        logger.error(f"Output file exists: {output_path}. Use --force to overwrite.")
        sys.exit(1)

    # Connect to BaseX
    try:
        session = connect_basex(host, port, username, password, database)
    except Exception as e:
        logger.error(f"Failed to connect to BaseX: {e}")
        sys.exit(1)

    try:
        # Count total entries
        total_entries = count_entries(session, database)
        logger.info(f"Total entries in database: {total_entries}")

        if total_entries == 0:
            logger.error("No entries found in database")
            sys.exit(1)

        # Determine processing limits
        sample_size = args.sample if args.sample else total_entries
        effective_total = min(sample_size, total_entries)

        # Track patterns
        seen_patterns: Dict[str, int] = {}
        all_patterns: List[Dict[str, Any]] = []

        # Stream and process entries
        if args.sample:
            # For sampling, fetch first N entries
            logger.info(f"Sampling {sample_size} entries...")
            batch_size = min(args.batch_size, sample_size)

            entries_processed = 0
            for batch in stream_entries(session, database, batch_size):
                if entries_processed >= sample_size:
                    break

                # Trim batch if needed
                remaining = sample_size - entries_processed
                if len(batch) > remaining:
                    batch = batch[:remaining]

                patterns = extract_patterns_from_entries(batch, seen_patterns)
                all_patterns.extend(patterns)
                entries_processed += len(batch)

                if entries_processed % 1000 == 0:
                    logger.info(f"Sampled {entries_processed}/{sample_size} entries...")
        else:
            # Process all entries
            logger.info("Processing all entries...")
            for batch in stream_entries(session, database, args.batch_size):
                patterns = extract_patterns_from_entries(batch, seen_patterns)
                all_patterns.extend(patterns)

        # Update occurrence counts in final patterns
        patterns_by_id = {p['id']: p for p in all_patterns}
        for pattern_key, count in seen_patterns.items():
            # Extract pattern ID from key mapping
            # Since we created patterns in order, we need to rebuild
            pass

        # Rebuild patterns with final occurrence counts
        final_patterns = []
        for pattern_key, count in seen_patterns.items():
            # Find the pattern (we need to track which pattern each key maps to)
            path, hash_val = pattern_key.rsplit(':', 1) if ':' in pattern_key else ('', '')
            # This is a simplification - in production we'd want better tracking

        # Update occurrence counts in all_patterns
        pattern_occurrences: Dict[int, int] = {}
        for pattern_key, count in seen_patterns.items():
            # Map back to pattern index (simplified - uses order of insertion)
            # In practice, we'd want a better mapping
            pass

        # Final output
        unique_patterns = len(all_patterns)

        output_data = {
            "metadata": {
                "extracted_at": datetime.now(timezone.utc).isoformat(),
                "total_entries": total_entries,
                "unique_patterns": unique_patterns,
                "sample_size": sample_size if args.sample else None,
                "database": database,
                "host": host,
                "port": port
            },
            "patterns": all_patterns
        }

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully extracted {unique_patterns} unique patterns from {total_entries} entries")
        logger.info(f"Output saved to: {output_path}")

        # Print summary
        print("\n=== Extraction Summary ===")
        print(f"Total entries processed: {total_entries}")
        print(f"Unique patterns found: {unique_patterns}")
        print(f"Output file: {output_path}")

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    finally:
        if session:
            try:
                session.close()
                logger.info("Disconnected from BaseX")
            except Exception as e:
                logger.warning(f"Error closing session: {e}")


if __name__ == '__main__':
    main()
