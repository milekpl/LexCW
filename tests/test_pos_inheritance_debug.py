"""Test POS inheritance functionality."""

from app.models.entry import Entry

def test_pos_inheritance():
    """Test POS inheritance with senses."""
    
    print("=== Testing POS Inheritance ===")
    
    # Test 1: Single sense with POS
    print("\n1. Single sense with POS:")
    entry1 = Entry(
        id_='test1',
        lexical_unit={'en': 'test'},
        senses=[{
            'id': 'sense1',
            'definition': {'en': 'test definition'},
            'grammatical_info': 'Noun'
        }]
    )
    print(f"Entry POS: {entry1.grammatical_info}")
    print(f"Sense POS: {entry1.senses[0].grammatical_info if entry1.senses else 'No senses'}")
    
    # Test 2: Multiple senses with same POS
    print("\n2. Multiple senses with same POS:")
    entry2 = Entry(
        id_='test2',
        lexical_unit={'en': 'test'},
        senses=[
            {
                'id': 'sense1',
                'definition': {'en': 'first definition'},
                'grammatical_info': 'Verb'
            },
            {
                'id': 'sense2', 
                'definition': {'en': 'second definition'},
                'grammatical_info': 'Verb'
            }
        ]
    )
    print(f"Entry POS: {entry2.grammatical_info}")
    print(f"Sense 1 POS: {entry2.senses[0].grammatical_info if len(entry2.senses) > 0 else 'No sense'}")
    print(f"Sense 2 POS: {entry2.senses[1].grammatical_info if len(entry2.senses) > 1 else 'No sense'}")
    
    # Test 3: Multiple senses with different POS
    print("\n3. Multiple senses with different POS:")
    entry3 = Entry(
        id_='test3',
        lexical_unit={'en': 'test'},
        senses=[
            {
                'id': 'sense1',
                'definition': {'en': 'first definition'},
                'grammatical_info': 'Noun'
            },
            {
                'id': 'sense2',
                'definition': {'en': 'second definition'},
                'grammatical_info': 'Verb'
            }
        ]
    )
    print(f"Entry POS: {entry3.grammatical_info}")
    print(f"Sense 1 POS: {entry3.senses[0].grammatical_info if len(entry3.senses) > 0 else 'No sense'}")
    print(f"Sense 2 POS: {entry3.senses[1].grammatical_info if len(entry3.senses) > 1 else 'No sense'}")
    
    # Test 4: Explicit entry POS
    print("\n4. Explicit entry POS (should override inheritance):")
    entry4 = Entry(
        id_='test4',
        lexical_unit={'en': 'test'},
        grammatical_info='Adjective',  # Explicit POS
        senses=[{
            'id': 'sense1',
            'definition': {'en': 'test definition'},
            'grammatical_info': 'Noun'
        }]
    )
    print(f"Entry POS: {entry4.grammatical_info}")
    print(f"Sense POS: {entry4.senses[0].grammatical_info if entry4.senses else 'No senses'}")

if __name__ == "__main__":
    test_pos_inheritance()
