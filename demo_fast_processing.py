"""
Simple fast corpus processor demo - performance test.
"""

import time
from app.services.fast_corpus_processor import FastCorpusProcessor
from app.models.corpus_batch import ProcessingConfig


def test_fast_processing_demo():
    """Demo fast corpus processing without spaCy dependencies."""
    
    # Mock connection (not actually used for linguistic processing)
    mock_conn = None
    
    # Create processor with optimized config
    config = ProcessingConfig(
        batch_size=10000,      # Large batches
        max_workers=4,         # Parallel processing
        cache_enabled=True,    # Enable caching
        spacy_model="en_core_web_sm"
    )
    
    processor = FastCorpusProcessor(mock_conn, config)
    
    # Generate test corpus (simulating real data)
    print("Generating test corpus...")
    test_sentences = [
        f"This is test sentence number {i} with various linguistic patterns and structures." 
        for i in range(20000)  # 20K sentences
    ]
    
    print(f"Processing {len(test_sentences)} sentences...")
    
    # Test performance
    start_time = time.time()
    result = processor.process_batch(test_sentences)
    total_time = time.time() - start_time
    
    # Print results
    print("\n=== PERFORMANCE RESULTS ===")
    print(f"Total sentences: {result.total_sentences}")
    print(f"Processed: {result.processed_sentences}")
    print(f"Failed: {result.failed_sentences}")
    print(f"Success rate: {result.success_rate:.1%}")
    print(f"Total time: {total_time:.2f} seconds")
    
    if result.processing_stats:
        stats = result.processing_stats
        print(f"Throughput: {stats.throughput_sentences_per_sec:.0f} sentences/sec")
        print(f"Avg time per sentence: {stats.avg_processing_time*1000:.2f} ms")
        print(f"Cache hit rate: {stats.cache_hit_rate:.1%}")
        print(f"Memory usage: {stats.memory_usage_mb:.1f} MB")
    
    # Performance targets
    print("\n=== PERFORMANCE TARGETS ===")
    target_throughput = 1000  # sentences per second
    actual_throughput = len(test_sentences) / total_time
    
    print(f"Target throughput: {target_throughput} sentences/sec")
    print(f"Actual throughput: {actual_throughput:.0f} sentences/sec")
    
    if actual_throughput >= target_throughput:
        print("✅ PERFORMANCE TARGET MET!")
    else:
        print("⚠️  Performance below target")
    
    # Test caching effectiveness
    print("\n=== CACHE EFFECTIVENESS TEST ===")
    repeated_sentence = "This sentence will be repeated for cache testing."
    cache_test_sentences = [repeated_sentence] * 1000
    
    start_time = time.time()
    cache_result = processor.process_batch(cache_test_sentences)
    cache_time = time.time() - start_time
    
    cache_throughput = len(cache_test_sentences) / cache_time
    print(f"Cache test throughput: {cache_throughput:.0f} sentences/sec")
    
    if cache_result.processing_stats:
        print(f"Cache hit rate: {cache_result.processing_stats.cache_hit_rate:.1%}")
    
    print("\n=== MEMORY EFFICIENCY TEST ===")
    cache_stats = processor.get_cache_stats()
    print(f"Total cache hits: {cache_stats['cache_hits']}")
    print(f"Total cache misses: {cache_stats['cache_misses']}")
    print(f"Overall hit rate: {cache_stats['hit_rate']:.1%}")
    print(f"Total processed: {cache_stats['total_processed']}")
    
    print("\n=== DEMO COMPLETE ===")
    return result


if __name__ == "__main__":
    test_fast_processing_demo()
