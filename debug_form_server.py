#!/usr/bin/env python3
"""
Test script to see exactly what JSON is being sent by the frontend form
"""

from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/debug-form', methods=['POST'])
def debug_form():
    """Debug endpoint to see what data is being sent"""
    print("=== DEBUG FORM DATA ===")
    print(f"Content-Type: {request.content_type}")
    print(f"Method: {request.method}")
    
    # Try to get JSON
    try:
        json_data = request.get_json()
        print(f"JSON Data: {json_data}")
        print(f"JSON Type: {type(json_data)}")
        
        if json_data and 'grammatical_info' in json_data:
            gi = json_data['grammatical_info']
            print(f"grammatical_info: {gi}")
            print(f"grammatical_info type: {type(gi)}")
            
    except Exception as e:
        print(f"JSON error: {e}")
    
    # Try form data
    if request.form:
        form_data = dict(request.form)
        print(f"Form Data: {form_data}")
    
    return jsonify({"status": "debug complete"})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
