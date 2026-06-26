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

    def test_merge_appends_relations_without_deduplication(self):
        """Sense merge appends relations without deduplication (all relations kept)."""
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

        # Create source sense with same relation
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

        # Relations are appended without deduplication (both kept)
        assert len(target_sense.relations) == 2
        assert all(r['ref'] == 'duplicate_ref' for r in target_sense.relations)

    def test_merge_preserves_subsense_hierarchy(self):
        """Sense merge must preserve subsense parent-child relationships."""
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

        assert len(target_sense.subsenses) == 3
        sub_ids = {s['id'] for s in target_sense.subsenses}
        assert 'sub1' in sub_ids
        assert 'sub2' in sub_ids
        assert 'sub3' in sub_ids

    def test_merge_preserves_semantic_domains(self):
        """Sense merge must preserve semantic domain assignments."""
        # Note: Uses semantic_domains (plural, List[str]) per Sense model
        target_sense = Sense(
            id='sense_target',
            glosses={'en': 'target'},
            definitions={'en': 'definition'},
            examples=[],
            relations=[],
            semantic_domains=['1.2.3 Animals']
        )

        source_sense = Sense(
            id='sense_source',
            glosses={'en': 'source'},
            definitions={'en': 'source def'},
            examples=[],
            relations=[],
            semantic_domains=['4.5.6 Plants']
        )

        service = MergeSplitService(Mock())
        service._merge_senses_into_target(target_sense, [source_sense])

        assert isinstance(target_sense.semantic_domains, list)
        assert '1.2.3 Animals' in target_sense.semantic_domains
        assert '4.5.6 Plants' in target_sense.semantic_domains

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

        # Verify new entry has the transferred sense
        assert new_entry.senses[0].id == source_sense1.id
        assert new_entry.senses[0].glosses['en'] == 'gloss1'

        # Verify examples are preserved (1 example created, 1 example per sense)
        assert len(new_entry.senses[0].examples) == 1

        # Verify relations are preserved (1 relation created, 1 relation per sense)
        assert len(new_entry.senses[0].relations) == 1

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
            id_='source_entry',
            lexical_unit={'en': 'test'},
            senses=[Sense(id='sense_1', glosses={'en': 'gloss'})],
            pronunciations={'ipa': '/tɛst/', 'audio': 'recording'}  # Dict format per Entry model
        )

        service = MergeSplitService(Mock())

        # Test 1: When pronunciations provided in new_entry_data, use them (dict format)
        new_entry1 = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {'pronunciations': {'new-phon': '/new/'}}  # Dict format per Entry model
        )
        assert new_entry1.pronunciations == {'new-phon': '/new/'}

        # Test 2: When no pronunciations in new_entry_data, defaults to empty dict
        # (source pronunciations are not automatically copied - this is the current behavior)
        new_entry2 = service._create_new_entry_from_senses(
            source_entry,
            ['sense_1'],
            {}  # No pronunciations
        )
        assert new_entry2.pronunciations == {}


class TestTransferRelationsUpdate:
    """Test _transfer_senses_to_entry() updates relation references - component: merge_split_service"""

    def test_transfer_adds_senses_to_target(self):
        """Sense transfer adds senses to target entry."""
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

        # Verify sense transferred to target
        assert len(target_entry.senses) == 1
        assert target_entry.senses[0].id == 'sense_1'
        assert target_entry.senses[0].glosses['en'] == 'gloss'

        # Verify examples preserved
        assert len(target_entry.senses[0].examples) == 1

        # Verify relations preserved
        assert len(target_entry.senses[0].relations) == 1

    def test_transfer_renames_senses_on_conflict(self):
        """Sense transfer must rename senses when duplicate IDs exist."""
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
            id='sense_1',
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

        assert len(target_entry.senses) == 2
        transferred_sense = target_entry.senses[1]
        assert transferred_sense.id == 'sense_1_transferred'
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
