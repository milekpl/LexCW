"""Check the current state of the AIDS test entry."""
from app import create_app
from app.database.basex_connector import BaseXConnector

app = create_app()

with app.app_context():
    from flask import current_app
    
    service = current_app.dictionary_service
    
    query = """
    for $entry in collection('dictionary')//entry[@id="AIDS test_a774b9c4-c013-4f54-9017-cf818791080c"]
    return $entry
    """
    
    result = service.connector.execute_query(query)
    print("Current entry XML:")
    print(result)
    print("\n" + "="*80 + "\n")
    
    # Parse and check senses
    from lxml import etree
    root = etree.fromstring(result.encode('utf-8'))
    
    print(f"Total senses: {len(root.findall('.//sense'))}")
    for i, sense in enumerate(root.findall('.//sense')):
        print(f"\nSense {i+1} (id={sense.get('id')}):")
        
        # Check definition
        definition = sense.find('definition')
        if definition is not None:
            print("  Definition forms:")
            for form in definition.findall('form'):
                lang = form.get('lang')
                text_elem = form.find('text')
                text = text_elem.text if text_elem is not None and text_elem.text else ""
                print(f"    {lang}: '{text}'")
        else:
            print("  No definition")
        
        # Check gloss
        gloss = sense.find('gloss')
        if gloss is not None:
            print("  Gloss forms:")
            for form in gloss.findall('form'):
                lang = form.get('lang')
                text_elem = form.find('text')
                text = text_elem.text if text_elem is not None and text_elem.text else ""
                print(f"    {lang}: '{text}'")
        else:
            print("  No gloss")
