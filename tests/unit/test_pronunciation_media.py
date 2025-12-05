"""
Unit tests for pronunciation media elements (Day 35).

Tests the media attribute on Entry model and Pronunciation model.
"""

import pytest
from app.models.entry import Entry
from app.models.pronunciation import Pronunciation


class TestPronunciationMediaAttribute:
    """Test the media attribute on Pronunciation model."""
    
    def test_pronunciation_has_media_attribute(self):
        """Test that Pronunciation model has media attribute."""
        pron = Pronunciation()
        assert hasattr(pron, 'media')
        assert isinstance(pron.media, list)
    
    def test_pronunciation_media_defaults_to_empty_list(self):
        """Test that media defaults to empty list."""
        pron = Pronunciation()
        assert pron.media == []
    
    def test_pronunciation_can_add_media_with_href_only(self):
        """Test adding media with just href."""
        pron = Pronunciation()
        pron.add_media('audio/word.mp3')
        
        assert len(pron.media) == 1
        assert pron.media[0]['href'] == 'audio/word.mp3'
        assert 'label' not in pron.media[0]
    
    def test_pronunciation_can_add_media_with_label(self):
        """Test adding media with href and multilingual label."""
        pron = Pronunciation()
        pron.add_media('audio/word.mp3', label={'en': 'Audio file', 'fr': 'Fichier audio'})
        
        assert len(pron.media) == 1
        assert pron.media[0]['href'] == 'audio/word.mp3'
        assert pron.media[0]['label']['en'] == 'Audio file'
        assert pron.media[0]['label']['fr'] == 'Fichier audio'
    
    def test_pronunciation_can_add_multiple_media(self):
        """Test adding multiple media items."""
        pron = Pronunciation()
        pron.add_media('audio/word1.mp3', label={'en': 'First audio'})
        pron.add_media('audio/word2.mp3', label={'en': 'Second audio'})
        
        assert len(pron.media) == 2
        assert pron.media[0]['href'] == 'audio/word1.mp3'
        assert pron.media[1]['href'] == 'audio/word2.mp3'


class TestEntryPronunciationMedia:
    """Test the pronunciation_media attribute on Entry model."""
    
    def test_entry_has_pronunciation_media_attribute(self):
        """Test that Entry model has pronunciation_media attribute."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'}
        )
        assert hasattr(entry, 'pronunciation_media')
        assert isinstance(entry.pronunciation_media, list)
    
    def test_entry_pronunciation_media_defaults_to_empty_list(self):
        """Test that pronunciation_media defaults to empty list."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'}
        )
        assert entry.pronunciation_media == []
    
    def test_entry_can_store_media_with_href_only(self):
        """Test storing media with just href."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            pronunciation_media=[
                {'href': 'audio/test.mp3'}
            ]
        )
        
        assert len(entry.pronunciation_media) == 1
        assert entry.pronunciation_media[0]['href'] == 'audio/test.mp3'
    
    def test_entry_can_store_media_with_label(self):
        """Test storing media with multilingual label."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            pronunciation_media=[
                {
                    'href': 'audio/test.mp3',
                    'label': {'en': 'Audio pronunciation', 'fr': 'Prononciation audio'}
                }
            ]
        )
        
        assert len(entry.pronunciation_media) == 1
        assert entry.pronunciation_media[0]['href'] == 'audio/test.mp3'
        assert entry.pronunciation_media[0]['label']['en'] == 'Audio pronunciation'
        assert entry.pronunciation_media[0]['label']['fr'] == 'Prononciation audio'
    
    def test_entry_can_store_multiple_media(self):
        """Test storing multiple media items."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            pronunciation_media=[
                {'href': 'audio/test1.mp3', 'label': {'en': 'First'}},
                {'href': 'audio/test2.mp3', 'label': {'en': 'Second'}},
                {'href': 'audio/test3.mp3'}
            ]
        )
        
        assert len(entry.pronunciation_media) == 3
        assert entry.pronunciation_media[0]['label']['en'] == 'First'
        assert entry.pronunciation_media[1]['label']['en'] == 'Second'
        assert 'label' not in entry.pronunciation_media[2]
    
    def test_entry_pronunciation_media_supports_urls(self):
        """Test that media href can be URLs."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            pronunciation_media=[
                {'href': 'https://example.com/audio/test.mp3'}
            ]
        )
        
        assert entry.pronunciation_media[0]['href'] == 'https://example.com/audio/test.mp3'
    
    def test_entry_pronunciation_media_supports_relative_paths(self):
        """Test that media href can be relative paths."""
        entry = Entry(
            id_='test1',
            lexical_unit={'en': 'test'},
            pronunciation_media=[
                {'href': 'media/audio/pronunciation.wav'}
            ]
        )
        
        assert entry.pronunciation_media[0]['href'] == 'media/audio/pronunciation.wav'
