#!/usr/bin/env python3
"""
Kindle Dictionary Generator for Lexicographic Curation Workbench
==================================================================

This script generates Kindle-compatible dictionary files from a 
Lexicographic Curation Workbench instance via its REST API.

Supported output formats:
- MOBI (for Kindle e-readers)
- AZW3 (for Kindle e-readers, newer format)
- HTML (intermediate format, can be used with KindleGen/Kindle Previewer)

Prerequisites:
--------------
    pip install requests jinja2

    For MOBI/AZW3 generation, you'll need either:
    - KindleGen (deprecated but functional)
    - Kindle Previewer 3 (recommended)
    - Calibre's ebook-convert

Usage Examples:
--------------
    # Generate HTML dictionary from LCW instance
    python kindle_generator.py --output my_dict.html

    # Generate MOBI (requires KindleGen in PATH)
    python kindle_generator.py --format mobi --output my_dict.mobi

    # Generate with custom title and author
    python kindle_generator.py --title "My Language Dictionary" \
                               --author "My Name" \
                               --output my_dict.html

    # Use specific LCW instance
    python kindle_generator.py --api-url http://lcw.example.com:5000 \
                               --api-key my_api_key \
                               --output dict.html

Output Format:
-------------
The generated dictionary follows the Kindle Dictionary format:
- Each entry becomes an <idx:entry> element
- Headwords are marked with <idx:orth>
- Definitions support basic HTML formatting
- Supports inflections/variants for lookup

Dictionary Markup Guide:
-----------------------
https://kdp.amazon.com/en_US/help/topic/G2HXJS944J37Q6G3

"""

import argparse
import json
import os
import re
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from datetime import datetime

import requests


# HTML template for Kindle dictionary
KINDLE_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" 
  "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" 
      xmlns:idx="www.amazon.com/YES"
      xmlns:mbp="https://kindlegen.s3.amazonaws.com/AmazonKindlePublishingGuidelines.pdf">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <title>{{ title }}</title>
    <style type="text/css">
        body {
            font-family: Georgia, "Times New Roman", serif;
            margin: 0.5em;
        }
        .dictionary {
            margin: 1em;
        }
        .entry {
            margin-bottom: 1em;
            page-break-inside: avoid;
        }
        .headword {
            font-size: 1.2em;
            font-weight: bold;
            color: #000;
            margin-bottom: 0.3em;
        }
        .pronunciation {
            font-style: italic;
            color: #666;
            margin-left: 0.5em;
        }
        .pos {
            font-style: italic;
            color: #333;
            margin-bottom: 0.3em;
        }
        .sense {
            margin-left: 1em;
            margin-bottom: 0.5em;
        }
        .sense-number {
            font-weight: bold;
            margin-right: 0.3em;
        }
        .definition {
            margin-bottom: 0.3em;
        }
        .example {
            margin-left: 1em;
            font-style: italic;
            color: #555;
            margin-top: 0.3em;
        }
        .example-translation {
            margin-left: 1em;
            color: #666;
        }
        .variant {
            font-style: italic;
            color: #444;
            margin-left: 0.5em;
        }
    </style>
</head>
<body>
    <mbp:frameset>
        <div class="dictionary">
            <h1>{{ title }}</h1>
            <p class="meta">{{ entries_count }} entries | Generated {{ generation_date }}</p>
            
            {% for entry in entries %}
            <idx:entry name="default" scriptable="yes" spell="yes">
                <idx:orth value="{{ entry.headword | escape }}">
                    {% for variant in entry.variants %}
                    <idx:iform name="" value="{{ variant | escape }}"/>
                    {% endfor %}
                </idx:orth>
                
                <div class="entry">
                    <div class="headword">
                        {{ entry.headword | escape }}
                        {% if entry.pronunciation %}
                        <span class="pronunciation">/{{ entry.pronunciation | escape }}/</span>
                        {% endif %}
                    </div>
                    
                    {% if entry.pos %}
                    <div class="pos">{{ entry.pos | escape }}</div>
                    {% endif %}
                    
                    {% for sense in entry.senses %}
                    <div class="sense">
                        {% if entry.senses|length > 1 %}
                        <span class="sense-number">{{ loop.index }}.</span>
                        {% endif %}
                        
                        {% if sense.gloss %}
                        <div class="definition">{{ sense.gloss | escape }}</div>
                        {% endif %}
                        
                        {% if sense.definition %}
                        <div class="definition">{{ sense.definition | escape }}</div>
                        {% endif %}
                        
                        {% for example in sense.examples %}
                        <div class="example">"{{ example.text | escape }}"</div>
                        {% if example.translation %}
                        <div class="example-translation">{{ example.translation | escape }}</div>
                        {% endif %}
                        {% endfor %}
                    </div>
                    {% endfor %}
                    
                    {% if entry.etymology %}
                    <div class="etymology">
                        <small>Etymology: {{ entry.etymology | escape }}</small>
                    </div>
                    {% endif %}
                </div>
            </idx:entry>
            {% endfor %}
        </div>
    </mbp:frameset>
</body>
</html>
'''


class LCWKindleGenerator:
    """Generator for Kindle-compatible dictionaries from LCW API."""
    
    def __init__(
        self, 
        api_url: Optional[str] = None, 
        api_key: Optional[str] = None
    ):
        """
        Initialize generator.
        
        Args:
            api_url: LCW API base URL
            api_key: API key for authentication
        """
        self.api_url = api_url or os.getenv('LCW_API_URL', 'http://localhost:5000')
        self.api_key = api_key or os.getenv('LCW_API_KEY')
        self.session = requests.Session()
        
        self.session.headers.update({
            'Accept': 'application/json'
        })
        
        if self.api_key:
            self.session.headers['X-API-Key'] = self.api_key
    
    def _api_get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make GET request to API."""
        url = urljoin(self.api_url, f'/api/{endpoint}')
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error: API request failed - {e}", file=sys.stderr)
            sys.exit(1)
    
    def fetch_entries(self) -> List[Dict[str, Any]]:
        """
        Fetch all dictionary entries from LCW API.
        
        Returns:
            List of entry dictionaries
        """
        print("Fetching entries from LCW API...")
        
        all_entries = []
        page = 1
        per_page = 100
        
        while True:
            result = self._api_get('entries', params={
                'page': page,
                'per_page': per_page
            })
            
            entries = result.get('entries', [])
            if not entries:
                break
            
            all_entries.extend(entries)
            
            # Check if we've fetched all entries
            total = result.get('total', 0)
            if len(all_entries) >= total:
                break
            
            page += 1
            
            if page % 10 == 0:
                print(f"  Fetched {len(all_entries)} entries...")
        
        print(f"Fetched {len(all_entries)} total entries")
        return all_entries
    
    def transform_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform LCW entry format to Kindle-friendly format.
        
        Args:
            entry: Entry dict from LCW API
            
        Returns:
            Transformed entry dict for Kindle template
        """
        # Get headword from lexical_unit (prefer English, fall back to first)
        lexical_unit = entry.get('lexical_unit', {})
        headword = lexical_unit.get('en', '') or list(lexical_unit.values())[0] if lexical_unit else ''
        
        # Get variants
        variants = []
        for variant in entry.get('variants', []):
            variant_form = variant.get('form', {})
            variant_text = variant_form.get('en', '') or list(variant_form.values())[0] if variant_form else ''
            if variant_text and variant_text != headword:
                variants.append(variant_text)
        
        # Get pronunciation
        pronunciations = entry.get('pronunciations', {})
        pronunciation = pronunciations.get('seh-fonipa', '') if isinstance(pronunciations, dict) else ''
        
        # Get POS
        pos = entry.get('grammatical_info', '')
        
        # Transform senses
        transformed_senses = []
        for sense in entry.get('senses', []):
            # Get gloss (prefer English, fall back to first)
            glosses = sense.get('gloss', {})
            gloss = glosses.get('en', '') or list(glosses.values())[0] if glosses else ''
            
            # Get definition (prefer English)
            definitions = sense.get('definition', {})
            definition = definitions.get('en', '') or list(definitions.values())[0] if definitions else ''
            
            # Transform examples
            examples = []
            for example in sense.get('examples', []):
                example_text = example.get('text', '')
                translation = example.get('translation', '')
                if example_text:
                    examples.append({
                        'text': example_text,
                        'translation': translation
                    })
            
            transformed_senses.append({
                'gloss': gloss,
                'definition': definition,
                'examples': examples
            })
        
        # Get etymology summary
        etymologies = entry.get('etymology', [])
        etymology = ''
        if etymologies:
            etym = etymologies[0]
            etym_type = etym.get('type', '')
            etym_source = etym.get('source', '')
            etym_form = etym.get('form', {})
            etym_text = list(etym_form.values())[0] if etym_form else ''
            etymology = f"{etym_type} from {etym_source}: {etym_text}".strip()
        
        return {
            'headword': headword,
            'variants': variants,
            'pronunciation': pronunciation,
            'pos': pos,
            'senses': transformed_senses,
            'etymology': etymology
        }
    
    def generate_html(
        self, 
        output_path: str,
        title: str = "Dictionary",
        author: str = "Unknown"
    ) -> str:
        """
        Generate Kindle-compatible HTML dictionary.
        
        Args:
            output_path: Path for output HTML file
            title: Dictionary title
            author: Dictionary author
            
        Returns:
            Path to generated HTML file
        """
        # Fetch and transform entries
        entries = self.fetch_entries()
        transformed_entries = [self.transform_entry(e) for e in entries]
        
        # Filter out entries without headwords
        transformed_entries = [e for e in transformed_entries if e['headword']]
        
        print(f"Processing {len(transformed_entries)} valid entries...")
        
        # Simple template substitution (no Jinja2 dependency)
        template_vars = {
            'title': title,
            'author': author,
            'entries_count': len(transformed_entries),
            'generation_date': datetime.now().strftime('%Y-%m-%d'),
        }
        
        html_content = self._render_template(
            KINDLE_TEMPLATE,
            template_vars,
            transformed_entries
        )
        
        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML dictionary generated: {output_path}")
        return output_path
    
    def _render_template(
        self, 
        template: str, 
        vars: Dict[str, Any],
        entries: List[Dict[str, Any]]
    ) -> str:
        """
        Simple template renderer for Kindle HTML.
        
        Args:
            template: Template string
            vars: Template variables
            entries: Entry data
            
        Returns:
            Rendered HTML string
        """
        # Basic variable substitution
        result = template
        for key, value in vars.items():
            result = result.replace('{{ ' + key + ' }}', str(value))
        
        # Render entries
        entries_html = []
        for entry in entries:
            entry_html = self._render_entry_template(entry)
            entries_html.append(entry_html)
        
        result = result.replace(
            '{% for entry in entries %}\n            {% endfor %}',
            '\n'.join(entries_html)
        )
        
        # Remove remaining template tags
        result = re.sub(r'{%\s*if[^%]+%\}[^}]*{%\s*endif\s*%}', '', result)
        result = re.sub(r'{%\s*for[^%]+%\}', '', result)
        result = re.sub(r'{%\s*endfor\s*%}', '', result)
        
        return result
    
    def _render_entry_template(self, entry: Dict[str, Any]) -> str:
        """Render a single entry to HTML."""
        lines = []
        
        # Entry start
        headword_escaped = self._escape_xml(entry['headword'])
        lines.append(f'            <idx:entry name="default" scriptable="yes" spell="yes">')
        
        # Orth with variants
        variant_ifs = []
        for variant in entry['variants']:
            var_escaped = self._escape_xml(variant)
            variant_ifs.append(f'                    <idx:iform name="" value="{var_escaped}"/>')
        
        lines.append(f'                <idx:orth value="{headword_escaped}">')
        lines.extend(variant_ifs)
        lines.append('                </idx:orth>')
        
        # Entry content
        lines.append('                <div class="entry">')
        
        # Headword with pronunciation
        lines.append('                    <div class="headword">')
        lines.append(f'                        {headword_escaped}')
        if entry['pronunciation']:
            pron_escaped = self._escape_xml(entry['pronunciation'])
            lines.append(f'                        <span class="pronunciation">/{pron_escaped}/</span>')
        lines.append('                    </div>')
        
        # POS
        if entry['pos']:
            pos_escaped = self._escape_xml(entry['pos'])
            lines.append(f'                    <div class="pos">{pos_escaped}</div>')
        
        # Senses
        for i, sense in enumerate(entry['senses'], 1):
            lines.append('                    <div class="sense">')
            
            if len(entry['senses']) > 1:
                lines.append(f'                        <span class="sense-number">{i}.</span>')
            
            if sense['gloss']:
                gloss_escaped = self._escape_xml(sense['gloss'])
                lines.append(f'                        <div class="definition">{gloss_escaped}</div>')
            
            if sense['definition']:
                def_escaped = self._escape_xml(sense['definition'])
                lines.append(f'                        <div class="definition">{def_escaped}</div>')
            
            # Examples
            for example in sense['examples']:
                text_escaped = self._escape_xml(example['text'])
                lines.append(f'                        <div class="example">"{text_escaped}"</div>')
                if example['translation']:
                    trans_escaped = self._escape_xml(example['translation'])
                    lines.append(f'                        <div class="example-translation">{trans_escaped}</div>')
            
            lines.append('                    </div>')
        
        # Etymology
        if entry['etymology']:
            ety_escaped = self._escape_xml(entry['etymology'])
            lines.append(f'                    <div class="etymology"><small>Etymology: {ety_escaped}</small></div>')
        
        lines.append('                </div>')
        lines.append('            </idx:entry>')
        
        return '\n'.join(lines)
    
    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters."""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )
    
    def convert_to_mobi(self, html_path: str, output_path: str) -> str:
        """
        Convert HTML to MOBI using KindleGen or Calibre.
        
        Args:
            html_path: Path to HTML file
            output_path: Desired output path
            
        Returns:
            Path to generated MOBI file
        """
        # Check for conversion tools
        kindlegen_path = self._find_kindlegen()
        calibre_path = self._find_calibre()
        
        if kindlegen_path:
            return self._convert_with_kindlegen(html_path, output_path, kindlegen_path)
        elif calibre_path:
            return self._convert_with_calibre(html_path, output_path, calibre_path)
        else:
            print("Error: No MOBI conversion tool found.", file=sys.stderr)
            print("Please install either:", file=sys.stderr)
            print("  - Kindle Previewer 3 (includes kindlegen)", file=sys.stderr)
            print("  - Calibre (ebook-convert)", file=sys.stderr)
            sys.exit(1)
    
    def _find_kindlegen(self) -> Optional[str]:
        """Find KindleGen executable."""
        # Common locations
        paths = [
            'kindlegen',
            '/usr/local/bin/kindlegen',
            '/opt/kindlegen/kindlegen',
            'C:\\Program Files\\Amazon\\Kindle Previewer 3\\lib\\fc\\bin\\kindlegen.exe',
            'C:\\Program Files (x86)\\Amazon\\Kindle Previewer 3\\lib\\fc\\bin\\kindlegen.exe',
        ]
        
        for path in paths:
            try:
                result = subprocess.run(
                    [path, '-locale', 'en'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 1:  # kindlegen returns 1 for help
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def _find_calibre(self) -> Optional[str]:
        """Find Calibre's ebook-convert."""
        paths = [
            'ebook-convert',
            '/usr/bin/ebook-convert',
            '/usr/local/bin/ebook-convert',
            'C:\\Program Files\\Calibre2\\ebook-convert.exe',
        ]
        
        for path in paths:
            try:
                result = subprocess.run(
                    [path, '--version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def _convert_with_kindlegen(
        self, 
        html_path: str, 
        output_path: str,
        kindlegen_path: str
    ) -> str:
        """Convert HTML to MOBI using KindleGen."""
        print("Converting to MOBI using KindleGen...")
        
        try:
            result = subprocess.run(
                [kindlegen_path, html_path, '-o', Path(output_path).name],
                capture_output=True,
                text=True,
                cwd=str(Path(output_path).parent)
            )
            
            if result.returncode in [0, 1]:  # 1 = warnings, 2 = errors
                print(f"MOBI generated: {output_path}")
                return output_path
            else:
                print(f"KindleGen error: {result.stderr}", file=sys.stderr)
                sys.exit(1)
                
        except subprocess.CalledProcessError as e:
            print(f"Error running KindleGen: {e}", file=sys.stderr)
            sys.exit(1)
    
    def _convert_with_calibre(
        self, 
        html_path: str, 
        output_path: str,
        calibre_path: str
    ) -> str:
        """Convert HTML to MOBI using Calibre."""
        print("Converting to MOBI using Calibre...")
        
        try:
            result = subprocess.run(
                [calibre_path, html_path, output_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            print(f"MOBI generated: {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            print(f"Error running ebook-convert: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate Kindle dictionary from LCW instance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  LCW_API_URL    LCW API base URL (default: http://localhost:5000)
  LCW_API_KEY    API key for authentication

Examples:
  %(prog)s --output my_dict.html
  %(prog)s --format mobi --output my_dict.mobi --title "My Dictionary"
        """
    )
    
    parser.add_argument(
        '--api-url',
        help='LCW API base URL'
    )
    parser.add_argument(
        '--api-key',
        help='API key for authentication'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output file path'
    )
    parser.add_argument(
        '--format',
        choices=['html', 'mobi', 'azw3'],
        default='html',
        help='Output format (default: html)'
    )
    parser.add_argument(
        '--title',
        default='Dictionary',
        help='Dictionary title'
    )
    parser.add_argument(
        '--author',
        default='Unknown',
        help='Dictionary author'
    )
    
    args = parser.parse_args()
    
    # Initialize generator
    generator = LCWKindleGenerator(
        api_url=args.api_url,
        api_key=args.api_key
    )
    
    # Generate HTML
    html_path = args.output
    if args.format in ['mobi', 'azw3']:
        # Generate to temp HTML first
        with tempfile.NamedTemporaryFile(
            suffix='.html', 
            delete=False,
            mode='w',
            encoding='utf-8'
        ) as f:
            html_path = f.name
    
    generator.generate_html(
        output_path=html_path,
        title=args.title,
        author=args.author
    )
    
    # Convert if needed
    if args.format == 'mobi':
        mobi_path = args.output
        if not mobi_path.endswith('.mobi'):
            mobi_path += '.mobi'
        generator.convert_to_mobi(html_path, mobi_path)
        
        # Clean up temp HTML
        if html_path != args.output:
            os.unlink(html_path)


if __name__ == '__main__':
    main()
