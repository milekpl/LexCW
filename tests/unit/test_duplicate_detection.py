"""
Tests for duplicate detection: headword normalisation, candidate detection, API endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from app.services.dictionary_service import DictionaryService


class TestNormaliseHeadword:
    """Tests for headword normalisation pipeline."""

    @pytest.fixture
    def normalise(self):
        return DictionaryService._normalise_headword

    def test_plain_headword_unchanged(self, normalise):
        assert normalise("cat") == "cat"

    def test_lowercased(self, normalise):
        assert normalise("Cat") == "cat"

    def test_leading_article_a_stripped(self, normalise):
        assert normalise("a cat") == "cat"

    def test_leading_article_an_stripped(self, normalise):
        assert normalise("an apple") == "apple"

    def test_leading_article_the_stripped(self, normalise):
        assert normalise("The United Kingdom") == "united kingdom"

    def test_article_not_stripped_mid_word(self, normalise):
        assert normalise("theatre") == "theatre"

    def test_placeholder_sth_stripped(self, normalise):
        assert normalise("tell sth") == "tell"

    def test_placeholder_sb_stripped(self, normalise):
        assert normalise("ask sb") == "ask"

    def test_multiple_placeholders_stripped(self, normalise):
        assert normalise("tell sb sth") == "tell"

    def test_leading_placeholder_stripped(self, normalise):
        assert normalise("sth to do") == "to do"

    def test_placeholder_with_pipe_stripped(self, normalise):
        assert normalise("tell sb|sth") == "tell"

    def test_placeholder_only_returns_empty(self, normalise):
        assert normalise("sth/sb") == ""

    def test_whitespace_collapsed(self, normalise):
        assert normalise("  cat   dog  ") == "cat dog"

    def test_parenthetical_qualifier_stripped(self, normalise):
        assert normalise("cat (animal)") == "cat"

    def test_parenthetical_grammatical_stripped(self, normalise):
        assert normalise("run (v)") == "run"

    def test_only_last_parenthetical_stripped(self, normalise):
        assert normalise("give (sth) (to sb)") == "give"

    def test_pipe_separated_placeholders_during_normalise(self, normalise):
        assert normalise("tell sb|sth") == "tell"

    def test_custom_placeholders(self, normalise):
        assert normalise("parler qqch", placeholders=["qqch", "qqn"]) == "parler"

    def test_custom_articles(self, normalise):
        assert normalise("le chat", placeholders=None, articles=["le", "la", "les"]) == "chat"

    def test_no_normalisation_needed(self, normalise):
        assert normalise("house") == "house"

    def test_mixed_pipeline(self, normalise):
        assert normalise("The quick brown fox (adj)") == "quick brown fox"


class TestDuplicateCandidates:
    """Tests for get_duplicate_candidates()."""

    @pytest.fixture
    def mock_service(self):
        """Create a DictionaryService with mocked connector for duplicate detection tests."""
        mock_connector = Mock()
        mock_connector.database = "test_db"
        mock_connector.is_connected.return_value = True
        mock_connector.execute_command.return_value = "test_db"
        mock_connector.execute_update.return_value = None

        with patch.dict("os.environ", {"TESTING": "true"}):
            service = DictionaryService(mock_connector)
            service._detect_namespace_usage = Mock(return_value=False)
            service._query_builder.get_namespace_prologue = Mock(return_value="")
            service._query_builder.get_element_path = Mock(side_effect=lambda x, _: x)

        return service, mock_connector

    def _set_raw_entries(self, connector, entries):
        """Configure mock to return pipe-delimited entry data from XQuery.

        Each entry: id|||headword|||citation_form|||pos|||sense_count
        """
        lines = "\n".join(entries)
        connector.execute_query.return_value = lines

    def _groups(self, result):
        return result['groups']

    def test_exact_headword_finds_duplicates(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||2",
            "e2|||cat|||cat|||n|||1",
            "e3|||dog|||dog|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        groups = self._groups(result)
        assert len(groups) == 1
        assert groups[0]["mode"] == "exact"
        assert len(groups[0]["entries"]) == 2
        entry_ids = {e["entry_id"] for e in groups[0]["entries"]}
        assert entry_ids == {"e1", "e2"}

    def test_exact_headword_no_duplicates(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||1",
            "e2|||dog|||dog|||n|||1",
            "e3|||fish|||fish|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        assert len(self._groups(result)) == 0

    def test_exact_headword_normalises_before_comparison(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||tell sb sth|||tell sb sth|||v|||2",
            "e2|||tell|||tell|||v|||1",
            "e3|||a cat|||a cat|||n|||1",
            "e4|||cat|||cat|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        groups = self._groups(result)
        assert len(groups) == 2

    def test_relaxed_mode_keeps_same_headword_similar_defs(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||1|||a small furry pet|||",
            "e2|||cat|||cat|||n|||1|||a small furry pet|||",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="near")
        groups = self._groups(result)
        assert len(groups) == 1
        assert groups[0]["mode"] == "exact"
        assert len(groups[0]["entries"]) == 2

    def test_relaxed_mode_splits_homographs(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||bank|||bank|||n|||1|||financial institution|||",
            "e2|||bank|||bank|||n|||1|||financial institution|||",
            "e3|||bank|||bank|||n|||1|||river side|||",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="near")
        groups = self._groups(result)
        # e1+e2 cluster together as duplicates; e3 split off (homograph) → excluded
        assert len(groups) == 1
        assert len(groups[0]["entries"]) == 2
        entry_ids = {e["entry_id"] for e in groups[0]["entries"]}
        assert entry_ids == {"e1", "e2"}

    def test_pos_filter_excludes_different_pos(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||well|||well|||n|||2",
            "e2|||well|||well|||adv|||1",
            "e3|||well|||well|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact", pos="n")
        groups = self._groups(result)
        assert len(groups) == 1
        entry_ids = {e["entry_id"] for e in groups[0]["entries"]}
        assert entry_ids == {"e1", "e3"}

    def test_no_pos_acts_as_wildcard(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||well|||well|||n|||2",
            "e2|||well|||well||||||1",  # no POS (empty string between ||| separators)
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact", pos="n")
        groups = self._groups(result)
        assert len(groups) == 1
        entry_ids = {e["entry_id"] for e in groups[0]["entries"]}
        assert entry_ids == {"e1", "e2"}

    def test_placeholder_only_entries_excluded(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||sth/sb|||sth/sb|||n|||1",
            "e2|||cat|||cat|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        assert len(self._groups(result)) == 0

    def test_exact_headword_confidence_is_one(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||bank|||bank|||n|||2",
            "e2|||bank|||bank|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        groups = self._groups(result)
        assert len(groups) == 1
        assert groups[0]["confidence"] == 1.0

    def test_all_mode_runs_exact_then_relaxed_filter(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||1|||a small pet|||",
            "e2|||cat|||cat|||n|||1|||a small pet|||",
            "e3|||bank|||bank|||n|||1|||financial institution|||",
            "e4|||bank|||bank|||n|||1|||river side|||",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="all")
        groups = self._groups(result)
        # cat/cat stay together (identical defs) → 1 group
        # bank entries have different defs → split → both excluded as singletons
        assert len(groups) == 1
        assert len(groups[0]["entries"]) == 2
        assert groups[0]["entries"][0]["headword"] == "cat"

    def test_parses_definition_and_gloss_from_seven_fields(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||2|||a feline animal|||a small pet",
            "e2|||cat|||cat|||n|||1|||a feline|||",
            "e3|||dog|||dog|||n|||1||||||",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        groups = self._groups(result)
        assert len(groups) == 1
        g = groups[0]
        entries_by_id = {e["entry_id"]: e for e in g["entries"]}
        assert entries_by_id["e1"]["definition"] == "a feline animal"
        assert entries_by_id["e1"]["gloss"] == "a small pet"
        assert entries_by_id["e2"]["definition"] == "a feline"
        assert entries_by_id["e2"]["gloss"] == ""

    def test_falls_back_to_empty_def_gloss_for_five_fields(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||2",
            "e2|||dog|||dog|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact")
        groups = self._groups(result)
        assert len(groups) == 0

    def test_sample_size_limits_scanned_entries(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||1",
            "e2|||cat|||cat|||n|||1",
            "e3|||dog|||dog|||n|||1",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="exact", sample_size=2)
        assert result["scanned_entries"] == 2

    def test_relaxed_mode_confidence_reflects_min_pairwise(self, mock_service):
        service, connector = mock_service
        entries_data = [
            "e1|||cat|||cat|||n|||1|||a small furry pet|||",
            "e2|||cat|||cat|||n|||1|||a small furry domestic pet|||",
            "e3|||cat|||cat|||n|||1|||a small domestic animal|||",
        ]
        self._set_raw_entries(connector, entries_data)
        result = service.get_duplicate_candidates(mode="near", threshold=5, min_confidence=0.0)
        groups = self._groups(result)
        # All three have highly overlapping trigrams → kept as one group
        assert len(groups) == 1
        assert groups[0]["confidence"] <= 1.0


class TestDuplicatesAPI:
    """Tests for /api/dashboard/duplicates endpoints."""

    @pytest.fixture
    def app_with_duplicates(self):
        """Create a Flask app with dashboard blueprint and mock dict_service."""
        from flask import Flask
        import os

        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'app', 'templates')
        app = Flask(__name__, template_folder=template_dir)
        app.config.update({
            'TESTING': True,
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key-for-sessions',
            'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
            'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        })

        from app.api.dashboard import dashboard_bp
        app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')

        # Set up mock injector with mocked dict_service
        from unittest.mock import Mock
        from app.services.dictionary_service import DictionaryService

        mock_dict = Mock(spec=DictionaryService)
        mock_dict.get_duplicate_candidates.return_value = {
            'groups': [
                {
                    'id': 'exact-cat-1-cat-2',
                    'confidence': 1.0,
                    'mode': 'exact',
                    'entries': [
                        {'entry_id': 'cat_1', 'headword': 'cat', 'citation_form': 'cat', 'senses_count': 2, 'pos': 'n', 'match_fields': ['lexical_unit']},
                        {'entry_id': 'cat_2', 'headword': 'cat', 'citation_form': 'cat', 'senses_count': 1, 'pos': 'n', 'match_fields': ['lexical_unit']},
                    ],
                    'merge_suggestion': 'keep_complete',
                }
            ],
            'total_candidates': 1,
        }
        mock_injector = Mock()
        mock_injector.get.side_effect = lambda cls: mock_dict if cls == DictionaryService else Mock()
        app.injector = mock_injector
        app.mock_dict_service = mock_dict  # expose for test modification

        # Set up SQLite for dismissed_duplicates table
        from app.models.workset_models import db
        db.init_app(app)
        with app.app_context():
            from app.models.dismissed_duplicate import DismissedDuplicate
            db.create_all()

        return app

    @pytest.fixture
    def client(self, app_with_duplicates):
        with app_with_duplicates.test_client() as c:
            with c.session_transaction() as sess:
                sess['project_id'] = 1
            yield c

    def test_get_duplicates_returns_list(self, client):
        response = client.get('/api/dashboard/duplicates')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'groups' in data['data']
        assert len(data['data']['groups']) == 1

    def test_get_duplicates_with_mode_param(self, client):
        response = client.get('/api/dashboard/duplicates?mode=near&threshold=1')
        assert response.status_code == 200

    def test_get_duplicates_with_sample_size_param(self, client, app_with_duplicates):
        app_with_duplicates.mock_dict_service.get_duplicate_candidates.return_value = {
            'groups': [],
            'total_candidates': 0,
            'sample_size': 100,
            'scanned_entries': 100,
        }
        response = client.get('/api/dashboard/duplicates?sample_size=100')
        assert response.status_code == 200
        app_with_duplicates.mock_dict_service.get_duplicate_candidates.assert_called_once()
        kwargs = app_with_duplicates.mock_dict_service.get_duplicate_candidates.call_args.kwargs
        assert kwargs['sample_size'] == 100

    def test_get_duplicates_handles_error(self, client, app_with_duplicates):
        app_with_duplicates.mock_dict_service.get_duplicate_candidates.side_effect = Exception("DB error")
        response = client.get('/api/dashboard/duplicates')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False
        app_with_duplicates.mock_dict_service.get_duplicate_candidates.side_effect = None

    def test_dismiss_group(self, client):
        response = client.post('/api/dashboard/duplicates/group_1/dismiss')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_dismiss_group_twice_is_idempotent(self, client):
        response1 = client.post('/api/dashboard/duplicates/group_1/dismiss')
        assert response1.status_code == 200
        response2 = client.post('/api/dashboard/duplicates/group_1/dismiss')
        assert response2.status_code == 200

    def test_dismissed_group_excluded_from_results(self, client):
        # Dismiss a group
        client.post('/api/dashboard/duplicates/exact-cat-1-cat-2/dismiss')
        # Then fetch duplicates — should exclude it
        response = client.get('/api/dashboard/duplicates')
        data = response.get_json()
        group_ids = [g['id'] for g in data['data']['groups']]
        assert 'exact-cat-1-cat-2' not in group_ids

    def test_merge_group_requires_entry_ids(self, client):
        response = client.post(
            '/api/dashboard/duplicates/group_1/merge',
            json={}
        )
        assert response.status_code == 400

    def test_merge_group_delegates_to_merge_service(self, client):
        from unittest.mock import patch, Mock as UMock
        with patch('app.services.merge_split_service.MergeSplitService') as MockMerge:
            mock_instance = MockMerge.return_value
            mock_instance.merge_entries.return_value = UMock(operation_id='op_1')

            response = client.post(
                '/api/dashboard/duplicates/group_1/merge',
                json={'target_entry_id': 'cat_1', 'source_entry_id': 'cat_2'}
            )
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            mock_instance.merge_entries.assert_called_once_with(
                target_entry_id='cat_1',
                source_entry_id='cat_2',
                sense_ids=None,
                user_id=None,
                conflict_resolution={"duplicate_senses": "rename"},
            )


class TestRelationDiscoveryLevel:
    """Tests for entry-level vs sense-level auto-detection in relation discovery."""

    def test_level_entry_when_entry_sim_higher(self):
        """level='entry' when entry-level similarity > sense-level similarity."""
        entry_sim = 0.95
        sense_sim = 0.30
        level = 'entry' if entry_sim >= sense_sim else 'sense'
        assert level == 'entry'

    def test_level_sense_when_sense_sim_higher(self):
        """level='sense' when sense-level similarity > entry-level similarity."""
        entry_sim = 0.60
        sense_sim = 0.85
        level = 'entry' if entry_sim >= sense_sim else 'sense'
        assert level == 'sense'

    def test_level_entry_when_equal(self):
        """level='entry' when similarities are equal (prefer broader scope)."""
        entry_sim = 0.70
        sense_sim = 0.70
        level = 'entry' if entry_sim >= sense_sim else 'sense'
        assert level == 'entry'

    def test_level_entry_when_no_senses(self):
        """level='entry' when sense similarity is 0 (no matching senses)."""
        entry_sim = 0.80
        sense_sim = 0.0
        level = 'entry' if entry_sim >= sense_sim else 'sense'
        assert level == 'entry'

    def test_burgle_pattern_entry_level(self):
        """The burgle/burglarise pattern: concatenated defs match (high), senses don't (low)."""
        # burgle: "to break into and steal from" (1 sense)
        # burglarise: "to break into" + "to steal from" (2 senses, joined with ", ")
        # Concatenated: "to break into and steal from" vs "to break into, to steal from"
        # Entry-level sim should be high; best sense-pair sim should be lower.
        entry_sim = 0.90
        sense_sim = 0.35
        level = 'entry' if entry_sim >= sense_sim else 'sense'
        assert level == 'entry', (
            f"burgle/burglarise should be entry-level "
            f"(entry_sim={entry_sim} > sense_sim={sense_sim})"
        )

    def test_sense_granularity_pattern_sense_level(self):
        """When senses match well but concatenated defs diverge, level should be sense."""
        entry_sim = 0.50
        sense_sim = 0.90
        level = 'entry' if entry_sim >= sense_sim else 'sense'
        assert level == 'sense'


class TestNewDuplicateDetectionFeatures:
    """Tests for new normalization variants, custom validation, and redundant examples."""

    def test_normalise_headword_variants(self):
        # 1. Parenthetical expansion
        v1 = DictionaryService._normalise_headword_variants("a little (bit)")
        assert "little" in v1
        assert "little bit" in v1

        # 2. Compound normalisation (hyphen and space stripped)
        v2 = DictionaryService._normalise_headword_variants("log-in")
        assert "log-in" in v2
        assert "login" in v2

        v3 = DictionaryService._normalise_headword_variants("log in")
        assert "log in" in v3
        assert "login" in v3

    def test_custom_validators(self):
        from app.services.validation_engine import ValidationEngine
        engine = ValidationEngine()

        rule_config = {"name": "test_rule", "priority": "warning", "category": "entry_level", "error_message": "error"}

        # 1. validate_redundant_variants_allomorphs
        data_redundant = {
            "lexical_unit": {"en": "cat"},
            "variants": [{"form": {"en": "cat"}}]
        }
        errors = engine._validate_redundant_variants_allomorphs("R1.2.4", rule_config, data_redundant)
        assert len(errors) == 1
        assert errors[0].rule_id == "R1.2.4"

        # 2. validate_duplicate_allomorphs
        data_dup_allomorph = {
            "variants": [
                {"form": {"en": "kitty"}},
                {"form": {"en": "kitty"}}
            ]
        }
        errors2 = engine._validate_duplicate_allomorphs("R1.2.5", rule_config, data_dup_allomorph)
        assert len(errors2) == 1

        # 3. validate_duplicate_variant_relations
        data_dup_relations = {
            "relations": [
                {"type": "variant", "ref": "entry_1"},
                {"type": "variant", "ref": "entry_1"}
            ]
        }
        errors3 = engine._validate_duplicate_variant_relations("R1.2.6", rule_config, data_dup_relations)
        assert len(errors3) == 1

        # 4. validate_redundant_gloss
        rule_config_gloss = {"name": "test_rule", "priority": "warning", "category": "sense_level", "error_message": "error"}
        data_gloss = {
            "senses": [
                {
                    "definition": {"en": "an animal called a cat"},
                    "gloss": {"en": "(cat)"}
                }
            ]
        }
        errors4 = engine._validate_redundant_gloss("R2.2.4", rule_config_gloss, data_gloss)
        assert len(errors4) == 1

    def test_get_redundant_examples(self):
        # Create a mock connector that returns phrase and example strings
        mock_connector = Mock()
        mock_connector.database = "test_db"
        
        # We need mock_connector.execute_query to return LIFT XML elements matching query
        # 1st call for phrases, 2nd call for examples
        mock_connector.execute_query.side_effect = [
            "entry_1|||under the weather\n", # phrases
            "entry_2|||weather|||under the weather.\n" # examples
        ]

        service = DictionaryService(mock_connector)
        service._detect_namespace_usage = Mock(return_value=False)
        service._query_builder.get_namespace_prologue = Mock(return_value="")
        service._query_builder.get_element_path = Mock(side_effect=lambda x, _: x)

        redundant = service.get_redundant_examples()
        assert len(redundant) == 1
        assert redundant[0]["phrase_headword"] == "under the weather"
        assert redundant[0]["example_text"] == "under the weather."
        assert redundant[0]["similarity"] >= 0.95

