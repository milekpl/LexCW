#!/usr/bin/env python3

from app.parsers.enhanced_lift_parser import EnhancedLiftParser
import tempfile
import os

sample_lift_content = '''<?xml version="1.0" encoding="UTF-8"?>
<lift version="0.15">
    <entry id="enhanced_parser_test">
        <lexical-unit>
            <form lang="en"><text>enhanced_test</text></form>
            <form lang="pl"><text>ulepszony_test</text></form>
        </lexical-unit>
        <sense id="enhanced_sense_1">
            <gloss lang="en"><text>Enhanced test gloss</text></gloss>
            <definition>
                <form lang="en"><text>Enhanced test definition</text></form>
            </definition>
            <grammatical-info value="Noun"/>
            <example>
                <form lang="en"><text>This is an enhanced example.</text></form>
                <translation>
                    <form lang="pl"><text>To jest ulepszony przykład.</text></form>
                </translation>
            </example>
        </sense>
    </entry>
</lift>'''

parser = EnhancedLiftParser()
with tempfile.NamedTemporaryFile(mode='w', suffix='.lift', delete=False, encoding='utf-8') as temp_file:
    temp_file.write(sample_lift_content)
    temp_path = temp_file.name

try:
    entries = parser.parse_file(temp_path)
    entry = entries[0]
    sense = entry.senses[0]
    print(f'Entry ID: {entry.id}')
    print(f'Sense ID: {sense.id}')
    print(f'Grammatical info: {sense.grammatical_info}')
    print(f'Number of examples: {len(sense.examples)}')
    if sense.examples:
        example = sense.examples[0]
        print(f'Example form: {example.form}')
        print(f'Example str: {str(example)}')
finally:
    os.unlink(temp_path)
