#!/usr/bin/env python3
"""
Performance Benchmarking Script for XML Direct Manipulation

This script measures the performance of key operations:
- Entry load time (GET operations)
- Entry save time (CREATE/UPDATE operations)
- Search performance (SEARCH queries)

Targets:
- Load time: ≤200ms
- Save time: ≤250ms
- Search time: ≤150ms (10 results)

Usage:
    python scripts/benchmark_xml_performance.py
    python scripts/benchmark_xml_performance.py --database test_dictionary
    python scripts/benchmark_xml_performance.py --iterations 50
    python scripts/benchmark_xml_performance.py --output report.json
"""

import argparse
import json
import statistics
import time
from datetime import datetime
from typing import Any

from app.database.basex_connector import BaseXConnector
from app.models.entry import Entry
from app.parsers.lift_parser import LIFTParser
from app.services.xml_entry_service import XMLEntryService


class PerformanceBenchmark:
    """Performance benchmarking for XML operations."""
    
    def __init__(self, database: str = "dictionary", iterations: int = 30):
        """
        Initialize benchmark.
        
        Args:
            database: Database name to test
            iterations: Number of iterations per test
        """
        self.database = database
        self.iterations = iterations
        self.connector = BaseXConnector("localhost", 1984, "admin", "admin")
        self.xml_service = XMLEntryService(
            host="localhost",
            port=1984,
            username="admin",
            password="admin",
            database=database
        )
        self.parser = LIFTParser()
        
        # Results storage
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "database": database,
            "iterations": iterations,
            "load_times": [],
            "save_times": [],
            "search_times": [],
            "summary": {}
        }
    
    def get_sample_entry_ids(self, count: int = 10) -> list[str]:
        """Get sample entry IDs from database."""
        # Use XML service to get entry IDs since connector needs session management
        try:
            results = self.xml_service.search_entries("*", limit=count)
            return [entry['id'] for entry in results]
        except Exception as e:
            print(f"Warning: Could not get sample entries: {e}")
            return []
    
    def create_test_entry_xml(self, index: int) -> str:
        """Create test entry XML for benchmarking."""
        entry_id = f"perf_test_{index}_{int(time.time() * 1000)}"
        guid = f"00000000-0000-0000-0000-{index:012d}"
        
        return f"""<entry dateCreated="2024-12-01T10:00:00Z" 
                       dateModified="2024-12-01T10:00:00Z"
                       id="{entry_id}"
                       guid="{guid}">
  <lexical-unit>
    <form lang="en"><text>benchmark test {index}</text></form>
  </lexical-unit>
  <sense id="sense_{index}_1" order="0">
    <grammatical-info value="Noun"/>
    <gloss lang="pl"><text>test wydajności {index}</text></gloss>
    <definition>
      <form lang="en"><text>A test entry for performance benchmarking</text></form>
    </definition>
  </sense>
  <sense id="sense_{index}_2" order="1">
    <grammatical-info value="Verb"/>
    <gloss lang="pl"><text>testować {index}</text></gloss>
    <example>
      <form lang="en"><text>This is an example sentence for testing.</text></form>
      <translation>
        <form lang="pl"><text>To jest przykładowe zdanie do testowania.</text></form>
      </translation>
    </example>
  </sense>
</entry>"""
    
    def benchmark_load(self) -> dict[str, Any]:
        """Benchmark entry load performance."""
        print("\n=== Benchmarking Entry Load ===")
        
        # Get sample entries
        entry_ids = self.get_sample_entry_ids(min(self.iterations, 20))
        if not entry_ids:
            print("No entries found in database for benchmarking")
            return {"error": "No entries found"}
        
        load_times = []
        
        for i in range(self.iterations):
            # Cycle through available entry IDs
            entry_id = entry_ids[i % len(entry_ids)]
            
            # Measure load time
            start = time.perf_counter()
            try:
                self.xml_service.get_entry(entry_id)
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                load_times.append(elapsed)
                
                if (i + 1) % 10 == 0:
                    print(f"Progress: {i + 1}/{self.iterations} loads")
            except Exception as e:
                print(f"Error loading entry {entry_id}: {e}")
        
        if not load_times:
            return {"error": "No successful loads"}
        
        results = {
            "count": len(load_times),
            "mean": statistics.mean(load_times),
            "median": statistics.median(load_times),
            "min": min(load_times),
            "max": max(load_times),
            "stdev": statistics.stdev(load_times) if len(load_times) > 1 else 0,
            "target": 200,
            "pass": statistics.mean(load_times) <= 200
        }
        
        print(f"\nLoad Performance:")
        print(f"  Mean: {results['mean']:.2f}ms")
        print(f"  Median: {results['median']:.2f}ms")
        print(f"  Min: {results['min']:.2f}ms")
        print(f"  Max: {results['max']:.2f}ms")
        print(f"  Target: {results['target']}ms")
        print(f"  Status: {'✅ PASS' if results['pass'] else '❌ FAIL'}")
        
        self.results["load_times"] = load_times
        return results
    
    def benchmark_save(self) -> dict[str, Any]:
        """Benchmark entry save (create/update) performance."""
        print("\n=== Benchmarking Entry Save ===")
        
        save_times = []
        created_ids = []
        
        # Test CREATE operations
        print("\nTesting CREATE operations...")
        for i in range(self.iterations // 2):
            xml = self.create_test_entry_xml(i)
            
            start = time.perf_counter()
            try:
                entry_id = self.xml_service.create_entry(xml)
                elapsed = (time.perf_counter() - start) * 1000
                save_times.append(elapsed)
                created_ids.append(entry_id)
                
                if (i + 1) % 5 == 0:
                    print(f"Progress: {i + 1}/{self.iterations // 2} creates")
            except Exception as e:
                print(f"Error creating entry: {e}")
        
        # Test UPDATE operations
        print("\nTesting UPDATE operations...")
        for i in range(min(len(created_ids), self.iterations // 2)):
            entry_id = created_ids[i]
            
            # Get current entry
            try:
                entry_data = self.xml_service.get_entry(entry_id)
                xml = self.create_test_entry_xml(i + 1000)  # Modified content
                xml = xml.replace(f"perf_test_{i + 1000}_", f"{entry_id.split('_')[0]}_test_{i}_")
                
                start = time.perf_counter()
                self.xml_service.update_entry(entry_id, xml)
                elapsed = (time.perf_counter() - start) * 1000
                save_times.append(elapsed)
                
                if (i + 1) % 5 == 0:
                    print(f"Progress: {i + 1}/{self.iterations // 2} updates")
            except Exception as e:
                print(f"Error updating entry {entry_id}: {e}")
        
        # Cleanup test entries
        print("\nCleaning up test entries...")
        for entry_id in created_ids:
            try:
                self.xml_service.delete_entry(entry_id)
            except Exception as e:
                print(f"Warning: Could not delete {entry_id}: {e}")
        
        if not save_times:
            return {"error": "No successful saves"}
        
        results = {
            "count": len(save_times),
            "mean": statistics.mean(save_times),
            "median": statistics.median(save_times),
            "min": min(save_times),
            "max": max(save_times),
            "stdev": statistics.stdev(save_times) if len(save_times) > 1 else 0,
            "target": 250,
            "pass": statistics.mean(save_times) <= 250
        }
        
        print(f"\nSave Performance:")
        print(f"  Mean: {results['mean']:.2f}ms")
        print(f"  Median: {results['median']:.2f}ms")
        print(f"  Min: {results['min']:.2f}ms")
        print(f"  Max: {results['max']:.2f}ms")
        print(f"  Target: {results['target']}ms")
        print(f"  Status: {'✅ PASS' if results['pass'] else '❌ FAIL'}")
        
        self.results["save_times"] = save_times
        return results
    
    def benchmark_search(self) -> dict[str, Any]:
        """Benchmark search performance."""
        print("\n=== Benchmarking Search ===")
        
        search_patterns = [
            "test",
            "accept*",
            "contest",
            "breath",
            "attest"
        ]
        
        search_times = []
        
        for i in range(self.iterations):
            pattern = search_patterns[i % len(search_patterns)]
            
            start = time.perf_counter()
            try:
                results = self.xml_service.search_entries(pattern, limit=10)
                elapsed = (time.perf_counter() - start) * 1000
                search_times.append(elapsed)
                
                if (i + 1) % 10 == 0:
                    print(f"Progress: {i + 1}/{self.iterations} searches")
            except Exception as e:
                print(f"Error searching for '{pattern}': {e}")
        
        if not search_times:
            return {"error": "No successful searches"}
        
        results = {
            "count": len(search_times),
            "mean": statistics.mean(search_times),
            "median": statistics.median(search_times),
            "min": min(search_times),
            "max": max(search_times),
            "stdev": statistics.stdev(search_times) if len(search_times) > 1 else 0,
            "target": 150,
            "pass": statistics.mean(search_times) <= 150
        }
        
        print(f"\nSearch Performance:")
        print(f"  Mean: {results['mean']:.2f}ms")
        print(f"  Median: {results['median']:.2f}ms")
        print(f"  Min: {results['min']:.2f}ms")
        print(f"  Max: {results['max']:.2f}ms")
        print(f"  Target: {results['target']}ms")
        print(f"  Status: {'✅ PASS' if results['pass'] else '❌ FAIL'}")
        
        self.results["search_times"] = search_times
        return results
    
    def run_all_benchmarks(self) -> dict[str, Any]:
        """Run all benchmarks and generate summary."""
        print(f"\n{'=' * 70}")
        print(f"XML DIRECT MANIPULATION - PERFORMANCE BENCHMARK")
        print(f"{'=' * 70}")
        print(f"Database: {self.database}")
        print(f"Iterations: {self.iterations}")
        print(f"Timestamp: {self.results['timestamp']}")
        
        # Run benchmarks
        load_results = self.benchmark_load()
        save_results = self.benchmark_save()
        search_results = self.benchmark_search()
        
        # Generate summary
        self.results["summary"] = {
            "load": load_results,
            "save": save_results,
            "search": search_results,
            "overall_pass": (
                load_results.get("pass", False) and
                save_results.get("pass", False) and
                search_results.get("pass", False)
            )
        }
        
        # Print summary
        print(f"\n{'=' * 70}")
        print(f"SUMMARY")
        print(f"{'=' * 70}")
        print(f"Load Performance:   {'✅ PASS' if load_results.get('pass') else '❌ FAIL'} "
              f"({load_results.get('mean', 0):.2f}ms avg, target: {load_results.get('target', 0)}ms)")
        print(f"Save Performance:   {'✅ PASS' if save_results.get('pass') else '❌ FAIL'} "
              f"({save_results.get('mean', 0):.2f}ms avg, target: {save_results.get('target', 0)}ms)")
        print(f"Search Performance: {'✅ PASS' if search_results.get('pass') else '❌ FAIL'} "
              f"({search_results.get('mean', 0):.2f}ms avg, target: {search_results.get('target', 0)}ms)")
        print(f"\nOverall: {'✅ ALL TARGETS MET' if self.results['summary']['overall_pass'] else '❌ OPTIMIZATION NEEDED'}")
        print(f"{'=' * 70}\n")
        
        return self.results
    
    def save_report(self, output_file: str):
        """Save benchmark results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"📄 Report saved to: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark XML Direct Manipulation performance"
    )
    parser.add_argument(
        "--database",
        default="dictionary",
        help="Database name to test (default: dictionary)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=30,
        help="Number of iterations per test (default: 30)"
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON report (optional)"
    )
    
    args = parser.parse_args()
    
    # Run benchmarks
    benchmark = PerformanceBenchmark(
        database=args.database,
        iterations=args.iterations
    )
    
    results = benchmark.run_all_benchmarks()
    
    # Save report if requested
    if args.output:
        benchmark.save_report(args.output)


if __name__ == "__main__":
    main()
