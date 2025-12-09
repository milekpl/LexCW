"""Add missing LIFT elements to existing display profiles."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.workset_models import db
from app.models.display_profile import DisplayProfile, ProfileElement
from app.services.lift_element_registry import LIFTElementRegistry
from run import app


def add_missing_elements_to_profiles():
    """Add translation and other missing elements to all profiles."""
    with app.app_context():
        registry = LIFTElementRegistry()
        
        # Elements to add with their configurations
        missing_elements = [
            ("translation", 80, "translation", "block", "if-content"),
            ("subsense", 35, "subsense", "block", "if-content"),
            ("reversal", 90, "reversal", "inline", "if-content"),
            ("note", 100, "note", "block", "if-content"),
            ("etymology", 110, "etymology", "block", "if-content"),
            ("variant", 120, "variant", "inline", "if-content"),
            ("relation", 130, "relation", "inline", "if-content"),
        ]
        
        profiles = DisplayProfile.query.all()
        updated_count = 0
        
        for profile in profiles:
            existing_elements = {elem.lift_element for elem in profile.elements}
            added_to_profile = False
            
            for elem_name, order, css_class, display_mode, visibility in missing_elements:
                if elem_name not in existing_elements:
                    elem_metadata = registry.get_element(elem_name)
                    if elem_metadata:
                        print(f"Adding '{elem_name}' to profile: {profile.name}")
                        
                        new_element = ProfileElement(
                            profile_id=profile.id,
                            lift_element=elem_name,
                            css_class=css_class,
                            visibility=visibility,
                            display_order=order,
                            language_filter='*',
                            prefix='',
                            suffix='',
                            config={'display_mode': display_mode}
                        )
                        
                        db.session.add(new_element)
                        added_to_profile = True
            
            if added_to_profile:
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✓ Updated {updated_count} profile(s)")
        else:
            print("\n✓ All profiles already have required elements")


if __name__ == '__main__':
    print("Adding missing LIFT elements to existing display profiles...")
    print("-" * 60)
    add_missing_elements_to_profiles()
