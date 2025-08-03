#!/usr/bin/env python3

"""
Real-Time Validation API Endpoints

Provides real-time validation for:
- Individual fields
- Form sections 
- Complete forms

Used by the frontend for immediate validation feedback.
"""

from flask import Blueprint, request, jsonify
import time
from typing import Dict, Any

# Create validation API blueprint
validation_api = Blueprint('validation_api', __name__)

class ValidationEngine:
    """Core validation engine for real-time validation"""
    
    @staticmethod
    def validate_field(field_name: str, value: Any, context: Dict) -> Dict:
        """
        Validate a single field
        
        Args:
            field_name: Name of the field being validated
            value: Value to validate
            context: Additional context (entry_id, form_data, etc.)
            
        Returns:
            Dict with validation results
        """
        errors = []
        warnings = []
        
        # Basic field validation rules
        if field_name == 'lexical_unit':
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append("Lexical unit is required")
            elif isinstance(value, str) and len(value.strip()) < 2:
                warnings.append("Lexical unit should be at least 2 characters")
            elif isinstance(value, dict):
                # Multilingual validation
                has_content = any(v and str(v).strip() for v in value.values())
                if not has_content:
                    errors.append("At least one language variant is required")
                    
        elif field_name == 'part_of_speech':
            if value and value not in ['noun', 'verb', 'adjective', 'adverb', 'preposition', 'conjunction', 'interjection', 'pronoun', 'article', 'numeral']:
                warnings.append("Unknown part of speech")
                
        elif field_name.endswith('_definition'):
            if value:
                if isinstance(value, dict):
                    for lang, definition in value.items():
                        if definition and len(str(definition).strip()) < 5:
                            warnings.append(f"Definition in {lang} seems very short")
                elif isinstance(value, str) and len(value.strip()) < 5:
                    warnings.append("Definition seems very short")
                    
        # Check for duplicates in context if applicable
        if field_name == 'lexical_unit' and context.get('form_data'):
            # This would check against existing entries in a real implementation
            pass
            
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'field': field_name,
            'value': value
        }
    
    @staticmethod
    def validate_section(section_name: str, fields: Dict, context: Dict) -> Dict:
        """
        Validate a form section
        
        Args:
            section_name: Name of the section
            fields: Dictionary of field_name -> value
            context: Additional context
            
        Returns:
            Dict with section validation results
        """
        field_results = {}
        section_errors = []
        section_warnings = []
        
        # Validate each field in the section
        for field_name, value in fields.items():
            field_result = ValidationEngine.validate_field(field_name, value, context)
            field_results[field_name] = field_result
            
        # Section-level validation rules
        if section_name == 'basic_info':
            # Check required fields for basic info
            required_fields = ['lexical_unit']
            for req_field in required_fields:
                if req_field not in fields or not fields[req_field]:
                    section_errors.append(f"Required field '{req_field}' is missing")
                    
        elif section_name == 'senses':
            # Validate sense definitions
            if not fields:
                section_warnings.append("No senses defined")
            else:
                sense_count = len([k for k in fields.keys() if 'definition' in k])
                if sense_count == 0:
                    section_warnings.append("At least one sense definition is recommended")
                    
        # Calculate overall section validity
        has_field_errors = any(not result['valid'] for result in field_results.values())
        section_valid = not has_field_errors and not section_errors
        
        return {
            'section_valid': section_valid,
            'field_results': field_results,
            'summary': {
                'errors': section_errors,
                'warnings': section_warnings,
                'total_fields': len(fields),
                'valid_fields': sum(1 for r in field_results.values() if r['valid']),
                'fields_with_warnings': sum(1 for r in field_results.values() if r['warnings'])
            }
        }
    
    @staticmethod
    def validate_form(entry_data: Dict) -> Dict:
        """
        Validate complete form data
        
        Args:
            entry_data: Complete entry data
            
        Returns:
            Dict with complete form validation results
        """
        errors = []
        warnings = []
        sections = {}
        
        # Extract sections from entry data
        basic_info_fields = {}
        if 'lexical_unit' in entry_data:
            basic_info_fields['lexical_unit'] = entry_data['lexical_unit']
        if 'part_of_speech' in entry_data:
            basic_info_fields['part_of_speech'] = entry_data['part_of_speech']
            
        # Validate basic info section
        if basic_info_fields:
            sections['basic_info'] = ValidationEngine.validate_section(
                'basic_info', basic_info_fields, {'entry_id': entry_data.get('id')}
            )
            
        # Validate senses section
        senses_fields = {}
        if 'senses' in entry_data:
            for i, sense in enumerate(entry_data['senses']):
                if 'definition' in sense:
                    senses_fields[f'sense_{i}_definition'] = sense['definition']
                    
        if senses_fields:
            sections['senses'] = ValidationEngine.validate_section(
                'senses', senses_fields, {'entry_id': entry_data.get('id')}
            )
            
        # Form-level validation
        if not entry_data.get('lexical_unit'):
            errors.append("Lexical unit is required for the entry")
            
        if not entry_data.get('senses'):
            warnings.append("Entry should have at least one sense")
            
        # Calculate overall validity
        section_errors = []
        for section_result in sections.values():
            if not section_result['section_valid']:
                section_errors.extend(section_result['summary']['errors'])
                
        form_valid = not errors and not section_errors
        
        return {
            'valid': form_valid,
            'errors': errors,
            'warnings': warnings,
            'sections': sections,
            'summary': {
                'total_sections': len(sections),
                'valid_sections': sum(1 for s in sections.values() if s['section_valid']),
                'total_errors': len(errors) + len(section_errors),
                'total_warnings': len(warnings) + sum(
                    len(s['summary']['warnings']) for s in sections.values()
                )
            }
        }

@validation_api.route('/field', methods=['POST'])
def validate_field():
    """
    Real-time field validation endpoint
    ---
    tags:
        - Validation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        field_name = data.get('field')
        value = data.get('value')
        context = data.get('context', {})
        
        if not field_name:
            return jsonify({'error': 'Field name is required'}), 400
            
        result = ValidationEngine.validate_field(field_name, value, context)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@validation_api.route('/section', methods=['POST'])
def validate_section():
    """
    Real-time section validation endpoint
    ---
    tags:
        - Validation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        section_name = data.get('section')
        fields = data.get('fields', {})
        context = data.get('context', {})
        
        if not section_name:
            return jsonify({'error': 'Section name is required'}), 400
            
        result = ValidationEngine.validate_section(section_name, fields, context)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@validation_api.route('/form', methods=['POST'])
def validate_form():
    """
    Complete form validation endpoint
    ---
    tags:
        - Validation
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        entry_data = data.get('entry_data', {})
        
        result = ValidationEngine.validate_form(entry_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check endpoint
@validation_api.route('/health', methods=['GET'])
def health_check():
    """
    Health check for validation API
    ---
    tags:
        - Validation
    """
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'endpoints': [
            '/api/validation/field',
            '/api/validation/section', 
            '/api/validation/form'
        ]
    })
