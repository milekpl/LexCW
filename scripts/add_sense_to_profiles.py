"""Add 'sense' element to existing display profiles that don't have it.

This script ensures all display profiles include the 'sense' element,
which is essential for hierarchical rendering and sense numbering with CSS counters.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.workset_models import db
from app.models.display_profile import DisplayProfile, ProfileElement
from app.services.lift_element_registry import LIFTElementRegistry
from run import app


def add_sense_element_to_profiles():
    """Add sense element to all profiles that don't have it."""
    with app.app_context():
        registry = LIFTElementRegistry()
        sense_element = registry.get_element('sense')
        
        if not sense_element:
            print("ERROR: 'sense' element not found in registry!")
            return
        
        # Get all profiles
        profiles = DisplayProfile.query.all()
        updated_count = 0
        
        for profile in profiles:
            # Check if profile already has 'sense' element
            has_sense = any(elem.lift_element == 'sense' for elem in profile.elements)
            
            if not has_sense:
                print(f"Adding 'sense' element to profile: {profile.name}")
                
                # Find appropriate display_order (after lexical-unit, before definition)
                # Use 25 as default (between 20 and 30)
                display_order = 25
                
                # Check if there's a definition element to insert before
                for elem in profile.elements:
                    if elem.lift_element == 'definition':
                        display_order = elem.display_order - 5
                        break
                
                # Create new sense element
                sense_profile_element = ProfileElement(
                    profile_id=profile.id,
                    lift_element='sense',
                    css_class='sense',
                    visibility='if-content',
                    display_order=display_order,
                    language_filter='*',
                    prefix='',
                    suffix='',
                    config={'display_mode': 'block'}
                )
                
                db.session.add(sense_profile_element)
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✓ Successfully added 'sense' element to {updated_count} profile(s)")
        else:
            print("\n✓ All profiles already have 'sense' element")


if __name__ == '__main__':
    print("Adding 'sense' element to existing display profiles...")
    print("-" * 60)
    add_sense_element_to_profiles()
