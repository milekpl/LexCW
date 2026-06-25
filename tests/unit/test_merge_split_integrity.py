"""
Data Path Integrity Tests - Merge and Split Operations
======================================================

Tests verifying data preservation during entry merge/split operations.
Addresses critical data paths 1-3 from the data path integrity audit.

Components Tested:
1. Sense merge field preservation (_merge_senses_into_target)
2. Entry split sense transfer (_create_new_entry_from_senses)
3. Transfer relations update (_transfer_senses_to_entry)

Usage:
    pytest tests/unit/test_merge_split_integrity.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.models.entry import Entry
from app.models.sense import Sense
from app.models.pronunciation import Pronunciation
from app.services.merge_split_service import MergeSplitService


class TestSenseMergeFieldPreservation:
    """Test _merge_senses_into_target() preserves all sense data - component: merge_split_service"""

    def test_merge_preserves_sense_glosses_all_languages(self):
        """Sense merge must preserve glosses in all languages, not just primary."""
        # Create target sense
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target', 'es': 'objetivo', 'fr': 'cible'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[]
        )

        # Create source sense with glosses in different languages
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source', 'de': 'quelle', 'pt': 'fonte'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[]
        )

        # Create mock service
        service = MergeSplitService(Mock())

        # Merge
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify all glosses preserved (unique keys combined)
        assert 'en' in target_sense.glosses  # English exists from both, combined
        assert 'es' in target_sense.glosses  # Spanish from target
        assert 'fr' in target_sense.glosses  # French from target
        assert 'de' in target_sense.glosses  # German from source
        assert 'pt' in target_sense.glosses  # Portuguese from source

    def test_merge_preserves_sense_examples(self):
        """Sense merge must preserve all examples with IDs and translations."""
        # Create target sense with examples
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[
                {'id': 'ex1', 'form': {'en': 'Target example 1'}},
                {'id': 'ex2', 'form': {'en': 'Target example 2'}}
            ],
            relations=[]
        )

        # Create source sense with examples
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[
                {'id': 'ex3', 'form': {'en': 'Source example 1'}},
                {'id': 'ex4', 'form': {'en': 'Source example 2'}}
            ],
            relations=[]
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify all examples preserved
        assert len(target_sense.examples) == 4
        example_ids = {ex['id'] for ex in target_sense.examples}
        assert 'ex1' in example_ids
        assert 'ex2' in example_ids
        assert 'ex3' in example_ids
        assert 'ex4' in example_ids

    def test_merge_preserves_sense_relations(self):
        """Sense merge must preserve all sense-level relations."""
        # Create target sense with relations
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[
                {'type': 'synonym', 'ref': 'syn1'},
                {'type': 'antonym', 'ref': 'ant1'}
            ]
        )

        # Create source sense with different relations
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[
                {'type': 'synonym', 'ref': 'syn2'},
                {'type': 'see_also', 'ref': 'see1'}
            ]
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify all relations preserved
        assert len(target_sense.relations) == 4
        relation_refs = {r['ref'] for r in target_sense.relations}
        assert 'syn1' in relation_refs
        assert 'ant1' in relation_refs
        assert 'syn2' in relation_refs
        assert 'see1' in relation_refs

    def test_merge_deduplicates_duplicate_relations(self):
        """Sense merge must deduplicate identical relations."""
        # Create target sense with relation
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[
                {'type': 'synonym', 'ref': 'duplicate_ref'}
            ]
        )

        # Create source sense with same relation (should be deduplicated)
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[
                {'type': 'synonym', 'ref': 'duplicate_ref'}  # Same as target
            ]
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify deduplication (only 1 relation, not 2)
        assert len(target_sense.relations) == 1
        assert target_sense.relations[0]['ref'] == 'duplicate_ref'

    def test_merge_preserves_subsense_hierarchy(self):
        """Sense merge must preserve subsense parent-child relationships."""
        # Create target sense with subsenses
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[],
            subsenses=[
                {'id': 'sub1', 'gloss': {'en': 'subsense 1'}},
                {'id': 'sub2', 'gloss': {'en': 'subsense 2'}}
            ]
        )

        # Create source sense with different subsenses
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[],
            subsenses=[
                {'id': 'sub3', 'gloss': {'en': 'subsense 3'}}
            ]
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify subsenses preserved
        assert len(target_sense.subsenses) == 3
        sub_ids = {s['id'] for s in target_sense.subsenses}
        assert 'sub1' in sub_ids
        assert 'sub2' in sub_ids
        assert 'sub3' in sub_ids

    def test_merge_preserves_semantic_domains(self):
        """Sense merge must preserve semantic domain assignments."""
        # Create target sense with semantic domain
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[],
            semantic_domain='1.2.3 Animals'
        )

        # Create source sense with different semantic domain
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[],
            semantic_domain='4.5.6 Plants'
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify semantic domains combined
        assert isinstance(target_sense.semantic_domain, list)
        assert '1.2.3 Animals' in target_sense.semantic_domain
        assert '4.5.6 Plants' in target_sense.semantic_domain

    def test_merge_preserves_grammatical_info(self):
        """Sense merge must preserve grammatical information."""
        # Create target sense WITHOUT grammatical info
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[],
            grammatical_info=''  # Empty
        )

        # Create source sense with grammatical info
        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[],
            grammatical_info='noun'
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        # Verify grammatical info copied from source
        assert target_sense.grammatical_info == 'noun'


class TestEntrySplitSenseTransfer:
    """Test _create_new_entry_from_senses() transfers all sense data - component: merge_split_service"""

    def test_split_creates_deep_copy_of_senses(self):
        """Split must create deep copies of senses, not share references."""
        # Create source entry with senses
        source_sense1 = Sense(
            id='sense_1',
            glosses={'en': 'gloss1'},
            definitions={'en': 'def1'},
            examples=[{'id': 'ex1', 'form': {'en': 'Example 1'}}],
            relations=[{'type': 'synonym', 'ref': 'ref1'}]
        )

        source_entry = Entry(
            id_='entry_1',
            lexical_unit={'en': 'test'},
            senses=[source_sense1]
        )

        # Create service and split
        service = MergeSplitService(Mock())
        new_entry = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {'lexical_unit': {'en': 'new headword'}}
        )

        # Verify new entry has different sense objects (not same reference)
        assert new_entry.senses[0] is not source_sense1

        # Verify examples are different objects
        assert new_entry.senses[0].examples[0] is not source_sense1.examples[0]

        # Verify relations are different objects
        assert new_entry.senses[0].relations[0] is not source_sense1.relations[0]

        # Modify new entry sense and verify source is unchanged
        new_entry.senses[0].glosses['en'] = 'modified'
        assert source_sense1.glosses['en'] == 'gloss1'  # Original unchanged

    def test_split_preserves_all_examples_in_transfer(self):
        """Split must preserve all examples when transferring senses to new entry."""
        source_sense = Sense(
            id='sense_1',
            glosses={'en': 'gloss'},
            definitions={'en': 'def'},
            examples=[
                {'id': 'ex1', 'form': {'en': 'Example 1'}, 'translation': {'es': 'Ejemplo 1'}},
                {'id': 'ex2', 'form': {'en': 'Example 2'}, 'translation': {'es': 'Ejemplo 2'}},
                {'id': 'ex3', 'form': {'en': 'Example 3'}}
            ],
            relations=[]
        )

        source_entry = Entry(
            id_='entry_1',
            lexical_unit={'en': 'test'},
            senses=[source_sense]
        )

        service = MergeSplitService(Mock())
        new_entry = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {}
        )

        # Verify all examples preserved
        assert len(new_entry.senses[0].examples) == 3
        example_ids = {ex['id'] for ex in new_entry.senses[0].examples}
        assert 'ex1' in example_ids
        assert 'ex2' in example_ids
        assert 'ex3' in example_ids

        # Verify translations preserved
        ex1 = next(ex for ex in new_entry.senses[0].examples if ex['id'] == 'ex1')
        assert ex1['translation']['es'] == 'Ejemplo 1'

    def test_split_preserves_sense_relations_after_transfer(self):
        """Split must preserve sense-level relations after transfer."""
        source_sense = Sense(
            id='sense_1',
            glosses={'en': 'gloss'},
            definitions={'en': 'def'},
            examples=[],
            relations=[
                {'type': 'synonym', 'ref': 'syn1', 'display': 'synonym word'},
                {'type': 'antonym', 'ref': 'ant1', 'display': 'opposite word'},
                {'type': 'see_also', 'ref': 'see1'}
            ]
        )

        source_entry = Entry(
            id_='entry_1',
            lexical_unit={'en': 'test'},
            senses=[source_sense]
        )

        service = MergeSplitService(Mock())
        new_entry = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {}
        )

        # Verify relations preserved
        assert len(new_entry.senses[0].relations) == 3
        relation_refs = {r['ref'] for r in new_entry.senses[0].relations}
        assert 'syn1' in relation_refs
        assert 'ant1' in relation_refs
        assert 'see1' in relation_refs

        # Verify display text preserved
        syn_rel = next(r for r in new_entry.senses[0].relations if r['ref'] == 'syn1')
        assert syn_rel['display'] == 'synonym word'

    def test_split_preserves_semantic_domains_after_transfer(self):
        """Split must preserve semantic domains after transfer."""
        source_sense = Sense(
            id='sense_1',
            glosses={'en': 'gloss'},
            definitions={'en': 'def'},
            examples=[],
            relations=[],
            semantic_domain='1.2.3 Animals'
        )

        source_entry = Entry(
            id_='entry_1',
            lexical_unit={'en': 'test'},
            senses=[source_sense]
        )

        service = MergeSplitService(Mock())
        new_entry = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {}
        )

        # Verify semantic domain preserved
        assert new_entry.senses[0].semantic_domain == '1.2.3 Animals'

    def test_split_preserves_subsense_structure(self):
        """Split must preserve subsense hierarchy in transferred senses."""
        source_sense = Sense(
            id='sense_1',
            glosses={'en': 'gloss'},
            definitions={'en': 'def'},
            examples=[],
            relations=[],
            subsenses=[
                {'id': 'sub1', 'gloss': {'en': 'sub 1'}, 'subsenses': [
                    {'id': 'sub1_1', 'gloss': {'en': 'nested sub 1'}}
                ]},
                {'id': 'sub2', 'gloss': {'en': 'sub 2'}}
            ]
        )

        source_entry = Entry(
            id_='entry_1',
            lexical_unit={'en': 'test'},
            senses=[source_sense]
        )

        service = MergeSplitService(Mock())
        new_entry = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {}
        )

        # Verify subsense structure preserved
        assert len(new_entry.senses[0].subsenses) == 2
        sub_ids = {s['id'] for s in new_entry.senses[0].subsenses}
        assert 'sub1' in sub_ids
        assert 'sub2' in sub_ids

        # Verify nested subsenses preserved
        sub1 = next(s for s in new_entry.senses[0].subsenses if s['id'] == 'sub1')
        assert len(sub1['subsenses']) == 1
        assert sub1['subsenses'][0]['id'] == 'sub1_1'

    def test_split_associates_pronunciations_with_new_entry(self):
        """Split must properly associate or copy pronunciations with new entry."""
        source_entry = Entry(
            id_='entry_1',
            lexical_unit={'en': 'test'},
            senses=[Sense(id='sense_1', glosses={'en': 'gloss'})],
            pronunciations=[
                {'type': 'ipa', 'value': '/tɛst/', 'audio_path': 'audio.mp3'},
                {'type': 'audio', 'value': 'recording', 'notes': 'Field recording'}
            ]
        )

        service = MergeSplitService(Mock())

        # Test 1: When pronunciations provided in new_entry_data, use them
        new_entry1 = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {'pronunciations': [{'type': 'ipa', 'value': '/new/'}]}
        )
        assert len(new_entry1.pronunciations) == 1
        assert new_entry1.pronunciations[0]['value'] == '/new/'

        # Test 2: When no pronunciations in new_entry_data, copy from source
        new_entry2 = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {}  # No pronunciations
        )
        assert len(new_entry2.pronunciations) == 2
        pron_values = {p['value'] for p in new_entry2.pronunciations}
        assert '/tɛst/' in pron_values
        assert 'recording' in pron_values


class TestTransferRelationsUpdate:
    """Test _transfer_senses_to_entry() updates relation references - component: merge_split_service"""

    def test_transfer_creates_deep_copy_of_senses(self):
        """Sense transfer must create deep copies, not share references."""
        source_sense = Sense(
            id='sense_1',
            glosses={'en': 'gloss'},
            definitions={'en': 'def'},
            examples=[{'id': 'ex1', 'form': {'en': 'Example'}}],
            relations=[{'type': 'synonym', 'ref': 'ref1'}]
        )

        target_entry = Entry(
            id_='target_entry',
            lexical_unit={'en': 'target'},
            senses=[]
        )

        service = MergeSplitService(Mock())
        service._transfer_senses_to_entry(target_entry, [source_sense])

        # Verify transferred sense is a different object
        assert target_entry.senses[0] is not source_sense

        # Verify examples are different objects
        assert target_entry.senses[0].examples[0] is not source_sense.examples[0]

        # Verify relations are different objects
        assert target_entry.senses[0].relations[0] is not source_sense.relations[0]

    def test_transfer_renames_senses_on_conflict(self):
        """Sense transfer must rename senses when duplicate IDs exist."""
        # Target already has a sense with id 'sense_1'
        existing_sense = Sense(
            id='sense_1',
            glosses={'en': 'existing'},
            definitions={'en': 'existing def'},
            examples=[],
            relations=[]
        )

        target_entry = Entry(
            id_='target_entry',
            lexical_unit={'en': 'target'},
            senses=[existing_sense]
        )

        # Source sense has same ID
        source_sense = Sense(
            id='sense_1',  # Same ID!
            glosses={'en': 'new'},
            definitions={'en': 'new def'},
            examples=[],
            relations=[{'type': 'synonym', 'ref': 'other', 'source': 'sense_1'}]
        )

        service = MergeSplitService(Mock())
        service._transfer_senses_to_entry(
            target_entry,
            [source_sense],
            conflict_resolution={'duplicate_senses': 'rename'}
        )

        # Verify renamed sense ID
        transferred_sense = target_entry.senses[1]  # Second sense (first is existing)
        assert transferred_sense.id == 'sense_1_transferred'

        # Verify relation source updated
        assert transferred_sense.relations[0]['source'] == 'sense_1_transferred'

    def test_transfer_skips_senses_on_conflict_when_configured(self):
        """Sense transfer must skip senses when skip conflict resolution configured."""
        existing_sense = Sense(
            id='sense_1',
            glosses={'en': 'existing'},
            definitions={'en': 'existing def'},
            examples=[],
            relations=[]
        )

        target_entry = Entry(
            id_='target_entry',
            lexical_unit={'en': 'target'},
            senses=[existing_sense]
        )

        source_sense = Sense(
            id='sense_1',  # Same ID
            glosses={'en': 'new'},
            definitions={'en': 'new def'},
            examples=[],
            relations=[]
        )

        service = MergeSplitService(Mock())
        service._transfer_senses_to_entry(
            target_entry,
            [source_sense],
            conflict_resolution={'duplicate_senses': 'skip'}
        )

        # Verify only 1 sense (existing), source sense skipped
        assert len(target_entry.senses) == 1
        assert target_entry.senses[0].glosses['en'] == 'existing'

    def test_transfer_preserves_all_sense_fields(self):
        """Sense transfer must preserve all sense fields including complex ones."""
        source_sense = Sense(
            id='sense_1',
            glosses={'en': 'gloss', 'es': 'glosa'},
            definitions={'en': 'definition', 'fr': 'définition'},
            examples=[
                {'id': 'ex1', 'form': {'en': 'Example 1'}, 'translation': {'es': 'Ejemplo 1'}},
                {'id': 'ex2', 'form': {'en': 'Example 2'}}
            ],
            relations=[
                {'type': 'synonym', 'ref': 'syn1', 'display': 'Synonym word'},
                {'type': 'antonym', 'ref': 'ant1'}
            ],
            grammatical_info='verb',
            semantic_domain='1.2.3 Animals',
            subsenses=[
                {'id': 'sub1', 'gloss': {'en': 'sub 1'}},
                {'id': 'sub2', 'gloss': {'en': 'sub 2'}}
            ]
        )

        target_entry = Entry(
            id_='target_entry',
            lexical_unit={'en': 'target'},
            senses=[]
        )

        service = MergeSplitService(Mock())
        service._transfer_senses_to_entry(target_entry, [source_sense])

        transferred = target_entry.senses[0]

        # Verify all fields preserved
        assert transferred.glosses['en'] == 'gloss'
        assert transferred.glosses['es'] == 'glosa'
        assert transferred.definitions['en'] == 'definition'
        assert transferred.definitions['fr'] == 'définition'
        assert len(transferred.examples) == 2
        assert len(transferred.relations) == 2
        assert transferred.grammatical_info == 'verb'
        assert transferred.semantic_domain == '1.2.3 Animals'
        assert len(transferred.subsenses) == 2
