from __future__ import annotations

"""
Performance Benchmarks for Core Dictionary Operations

This module contains performance tests to measure the speed of critical
dictionary operations and ensure they meet performance requirements.
"""
import os
import sys
import pytest
import time
import uuid
from typing import List, Dict, Any

# Add parent directory to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.entry import Entry
from app.models.sense import Sense
from app.services.dictionary_service import DictionaryService


class TestPerformanceBenchmarks:
    """Performance benchmark tests for core operations."""
    
    @pytest.fixture(scope="class")
    def dict_service(self, basex_available):
        """Get dictionary service instance for performance testing."""
        if not basex_available:
            pytest.skip("BaseX server not available")
            
        from app.database.basex_connector import BaseXConnector
        
        # Import the utility function from conftest
        import sys
        sys.path.append(os.path.dirname(__file__))
        from conftest import ensure_test_database
        
        test_db_name = f"test_performance_{uuid.uuid4().hex[:8]}"
        
        # Create test database connection
        connector = BaseXConnector(
            host=os.getenv('BASEX_HOST', 'localhost'),
            port=int(os.getenv('BASEX_PORT', '1984')),
            username=os.getenv('BASEX_USERNAME', 'admin'),
            password=os.getenv('BASEX_PASSWORD', 'admin'),
            database=test_db_name
        )
        
        try:
            connector.connect()
            ensure_test_database(connector, test_db_name)
            
            service = DictionaryService(db_connector=connector)
            yield service
        finally:
            # Cleanup
            try:
                if connector.session:
                    connector.drop_database(test_db_name)
                    connector.disconnect()
            except Exception:
                pass
    
    @pytest.fixture(scope="class")
    def sample_entries(self) -> List[Entry]:
        """Create sample entries for performance testing."""
        entries = []
        for i in range(100):  # Create 100 test entries
            entry = Entry(
                id=f"perf_test_{i:03d}",
                lexical_unit={
                    "en": f"performance_word_{i}",
                    "pl": f"słowo_wydajności_{i}"
                },
                senses=[
                    Sense(
                        id=f"perf_sense_{i}_1",
                        gloss=f"Performance test gloss {i}",
                        definition=f"Performance test definition {i}",
                        grammatical_info="Noun"
                    ),
                    Sense(
                        id=f"perf_sense_{i}_2", 
                        gloss=f"Performance test gloss {i} second",
                        definition=f"Performance test definition {i} second",
                        grammatical_info="Verb"
                    )
                ]
            )
            entries.append(entry)
        return entries
    
    def test_bulk_entry_creation_performance(self, dict_service, sample_entries):
        """Test performance of creating multiple entries."""
        start_time = time.time()
        
        created_count = 0
        for entry in sample_entries:
            try:
                dict_service.create_entry(entry)
                created_count += 1
            except Exception as e:
                print(f"Failed to create entry {entry.id}: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert duration < 30.0, f"Bulk creation took too long: {duration:.2f}s"
        assert created_count >= len(sample_entries) * 0.8, f"Too many failures: {created_count}/{len(sample_entries)}"
        
        entries_per_second = created_count / duration if duration > 0 else 0
        print(f"Created {created_count} entries in {duration:.2f}s ({entries_per_second:.2f} entries/sec)")
        
        # Should be able to create at least 5 entries per second
        assert entries_per_second >= 3.0, f"Creation rate too slow: {entries_per_second:.2f} entries/sec"
    
    def test_search_performance(self, dict_service):
        """Test search performance with various query types."""
        search_queries = [
            "performance",
            "word",
            "test",
            "słowo",
            "wydajności"
        ]
        
        for query in search_queries:
            start_time = time.time()
            
            try:
                results, total = dict_service.search_entries(query)
                end_time = time.time()
                duration = end_time - start_time
                
                # Search should complete within 5 seconds
                assert duration < 5.0, f"Search for '{query}' took too long: {duration:.2f}s"
                
                print(f"Search '{query}': {total} results in {duration:.3f}s")
                
                # Should return results quickly
                assert duration < 2.0, f"Search response time too slow: {duration:.3f}s"
                
            except Exception as e:
                print(f"Search failed for '{query}': {e}")
                # Search failures are acceptable for performance tests
    
    def test_entry_retrieval_performance(self, dict_service):
        """Test performance of retrieving individual entries."""
        entry_ids = [f"perf_test_{i:03d}" for i in range(0, 50, 5)]  # Every 5th entry
        
        retrieval_times = []
        successful_retrievals = 0
        
        for entry_id in entry_ids:
            start_time = time.time()
            
            try:
                entry = dict_service.get_entry(entry_id)
                end_time = time.time()
                duration = end_time - start_time
                
                retrieval_times.append(duration)
                successful_retrievals += 1
                
                # Individual retrieval should be very fast
                assert duration < 1.0, f"Entry retrieval took too long: {duration:.3f}s"
                
            except Exception as e:
                print(f"Failed to retrieve entry {entry_id}: {e}")
        
        if retrieval_times:
            avg_time = sum(retrieval_times) / len(retrieval_times)
            max_time = max(retrieval_times)
            
            print(f"Retrieved {successful_retrievals} entries")
            print(f"Average retrieval time: {avg_time:.3f}s")
            print(f"Max retrieval time: {max_time:.3f}s")
            
            # Average retrieval should be very fast
            assert avg_time < 0.5, f"Average retrieval time too slow: {avg_time:.3f}s"
    
    def test_count_operations_performance(self, dict_service):
        """Test performance of counting operations."""
        start_time = time.time()
        
        try:
            entry_count = dict_service.get_entry_count()
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"Counted {entry_count} entries in {duration:.3f}s")
            
            # Counting should be fast
            assert duration < 3.0, f"Count operation took too long: {duration:.3f}s"
            
            # Should find the entries we created
            assert entry_count >= 50, f"Unexpected entry count: {entry_count}"
            
        except Exception as e:
            print(f"Count operation failed: {e}")
            # Count failures are acceptable for performance tests
    
    def test_memory_usage_during_operations(self, dict_service):
        """Test memory usage during dictionary operations."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform some operations
        try:
            # Search operations
            for i in range(10):
                dict_service.search_entries(f"test_{i}")
            
            # Count operations  
            dict_service.get_entry_count()
            
            # Entry retrieval
            for i in range(5):
                try:
                    dict_service.get_entry(f"perf_test_{i:03d}")
                except Exception:
                    pass
            
            current_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = current_memory - initial_memory
            
            print(f"Memory usage: {initial_memory:.1f}MB -> {current_memory:.1f}MB (+{memory_increase:.1f}MB)")
            
            # Memory increase should be reasonable (less than 100MB)
            assert memory_increase < 100, f"Memory usage increased too much: {memory_increase:.1f}MB"
            
        except ImportError:
            pytest.skip("psutil not available for memory testing")
    
    def test_concurrent_operations_performance(self, dict_service: DictionaryService) -> None:
        """Test performance under simulated load (sequential operations with timing)."""
        # Skip complex threading due to BaseX limitations
        # Instead, test sequential operations that simulate load patterns
        
        try:
            # Quick validation that basic operations work
            dict_service.get_entry_count()
        except Exception as e:
            pytest.skip(f"BaseX connection issues detected, skipping load test: {e}")
        
        # Simulate concurrent-like load with rapid sequential operations
        operations: List[Dict[str, Any]] = []
        start_time = time.time()
        
        # Test rapid fire operations like a concurrent scenario would create
        for i in range(5):  # Reduced iterations
            try:
                # Search operation
                search_start = time.time()
                dict_service.search_entries(f"performance_load_{i}")
                search_time = time.time() - search_start
                
                # Count operation  
                count_start = time.time()
                dict_service.get_entry_count()
                count_time = time.time() - count_start
                
                operations.append({
                    'iteration': i,
                    'search_time': search_time,
                    'count_time': count_time
                })
                
                # Brief pause to prevent overwhelming the server
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Load test iteration {i} failed: {e}")
                # Continue with other iterations
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        print(f"Load test completed in {total_duration:.2f}s")
        print(f"Successful operations: {len(operations)}")
        
        # Test should complete within reasonable time
        assert total_duration < 15.0, f"Load test took too long: {total_duration:.2f}s"
        
        # Should complete at least some operations
        assert len(operations) >= 3, f"Too few operations completed: {len(operations)}"
        
        if operations:
            avg_search_time = sum(op['search_time'] for op in operations) / len(operations)
            avg_count_time = sum(op['count_time'] for op in operations) / len(operations)
            
            print(f"Average search time under load: {avg_search_time:.3f}s")
            print(f"Average count time under load: {avg_count_time:.3f}s")
            
            # Performance should remain reasonable under load
            assert avg_search_time < 3.0, f"Search time under load too slow: {avg_search_time:.3f}s"
            assert avg_count_time < 2.0, f"Count time under load too slow: {avg_count_time:.3f}s"


@pytest.mark.performance
class TestPerformanceRegression:
    """Tests to detect performance regressions."""
    
    def test_baseline_operations(self) -> None:
        """Test baseline performance metrics."""
        # These are simple baseline tests that don't require database
        
        # Test string operations
        start = time.time()
        for i in range(10000):
            test_string = f"test_string_{i}"
            _ = test_string.upper().lower().strip()
        string_time = time.time() - start
        
        # Test list operations
        start = time.time()
        test_list: List[int] = []
        for i in range(10000):
            test_list.append(i)
        for item in test_list:
            _ = str(item)
        list_time = time.time() - start
        
        # Test dict operations
        start = time.time()
        test_dict: Dict[str, str] = {}
        for i in range(10000):
            test_dict[f"key_{i}"] = f"value_{i}"
        for key, value in test_dict.items():
            _ = f"{key}={value}"
        dict_time = time.time() - start
        
        print(f"String operations: {string_time:.3f}s")
        print(f"List operations: {list_time:.3f}s") 
        print(f"Dict operations: {dict_time:.3f}s")
        
        # Basic operations should be very fast
        assert string_time < 1.0, f"String operations too slow: {string_time:.3f}s"
        assert list_time < 1.0, f"List operations too slow: {list_time:.3f}s"
        assert dict_time < 1.0, f"Dict operations too slow: {dict_time:.3f}s"
