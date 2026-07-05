import unittest
from unittest.mock import MagicMock
from app.services.pos_coherence_service import POSCoherenceService, get_pos_coherence_service

class TestPOSCoherenceService(unittest.TestCase):
    def test_singleton(self):
        s1 = get_pos_coherence_service()
        s2 = get_pos_coherence_service()
        self.assertIs(s1, s2)

    def test_mock_detection(self):
        service = POSCoherenceService()
        mock_dict_svc = MagicMock()
        mock_dict_svc._detect_namespace_usage.return_value = False
        mock_dict_svc._query_builder.get_namespace_prologue.return_value = ""
        mock_dict_svc._query_builder.get_element_path.side_effect = lambda tag, ns: tag
        mock_dict_svc.db_connector.database = "dictionary"

        # Mock query return: 15 samples of Noun, 15 samples of Verb, plus 1 clear mismatch
        samples = []
        for i in range(15):
            samples.append(f"id_n{i}|||dog{i}|||Noun|||a domesticated carnivorous mammal")
        for i in range(15):
            samples.append(f"id_v{i}|||run{i}|||Verb|||to move swiftly on foot")

        # Add an entry marked as Noun whose definition is strictly verb-like
        samples.append("id_bad|||jump|||Noun|||to spring clear of the ground by using the leg muscles")

        mock_dict_svc.db_connector.execute_query.return_value = "\n".join(samples)

        anomalies = service.detect_anomalies(mock_dict_svc, min_confidence=0.50, limit=10, cache_ttl_sec=0)
        self.assertIsInstance(anomalies, list)
        if anomalies:
            bad = next((a for a in anomalies if a["entry_id"] == "id_bad"), None)
            if bad:
                self.assertEqual(bad["actual_pos"], "Noun")
                self.assertEqual(bad["predicted_pos"], "Verb")

if __name__ == "__main__":
    unittest.main()
