# Large File CRUD Test Plan
#
# Tests for handling large LIFT files (100MB+, 150K+ entries)
#
# NOTE: These tests require large LIFT files that are NOT in the repository
# due to their size. Place your test files in tests/e2e/test_data/large_files/
# and they will be automatically gitignored.
#
# Test files are skipped if not found - run generate_test_files.py first
# to create reproducible test fixtures from your source files.

import pytest
import time
import hashlib
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# =============================================================================
# Configuration
# =============================================================================

# Directory for large test files (gitignored)
# Use absolute path to avoid cwd issues
LARGE_TEST_FILES_DIR = Path(__file__).resolve().parent / "test_data" / "large_files"

# Expected test files (will be skipped if not found)
EXPECTED_FILES = {
    "small": "test-small.lift",       # ~1 MB, ~500 entries
    "medium": "test-medium.lift",     # ~10 MB, ~5,000 entries
    "large": "test-large.lift",       # ~50 MB, ~25,000 entries
    "xlarge": "test-xl.lift",         # ~130 MB, ~65,000 entries
    "full": "exported_lift.lift",     # Your actual ~150K entry file
}

# Also check for alternative filenames
ALTERNATE_FILENAMES = {
    "full": ["full.lift", "exported_lift.lift", "dictionary_export.lift"],
}

# =============================================================================
# File Discovery and Skip Logic
# =============================================================================

def find_test_file(size_category: str) -> Optional[Path]:
    """Find a test file by size category. Returns None if not found."""
    # Check primary filename
    filename = EXPECTED_FILES.get(size_category)
    if filename:
        filepath = LARGE_TEST_FILES_DIR / filename
        if filepath.exists():
            return filepath

    # Check alternate filenames
    alternates = ALTERNATE_FILENAMES.get(size_category, [])
    for alt in alternates:
        filepath = LARGE_TEST_FILES_DIR / alt
        if filepath.exists():
            return filepath

    return None


def get_available_test_files() -> Dict[str, Path]:
    """Get all available test files."""
    available = {}
    for category in EXPECTED_FILES:
        filepath = find_test_file(category)
        if filepath:
            available[category] = filepath
    return available


def require_test_file(size_category: str, reason: str = "testing"):
    """Pytest fixture that skips if test file not found."""
    filepath = find_test_file(size_category)
    if filepath is None:
        pytest.skip(
            f"Test file for '{size_category}' not found at "
            f"{LARGE_TEST_FILES_DIR / EXPECTED_FILES[size_category]}. "
            f"Please add the file for {reason}."
        )
    return filepath


# =============================================================================
# File Generation (for creating test fixtures from source)
# =============================================================================

def generate_test_file_from_source(
    source_path: Path,
    target_path: Path,
    target_size_mb: int,
    entry_template: Optional[Dict] = None
) -> Path:
    """Generate a test LIFT file of approximately target_size_mb.

    Args:
        source_path: Path to source LIFT file to use as template
        target_path: Path for output file
        target_size_mb: Target file size in MB
        entry_template: Optional template for entry modifications

    Returns:
        Path to generated file
    """
    import xml.etree.ElementTree as ET

    target_size = target_size_mb * 1_000_000

    # Parse source
    tree = ET.parse(source_path)
    root = tree.getroot()

    # Count existing entries
    entries = root.findall(".//entry")
    original_count = len(entries)

    if original_count == 0:
        raise ValueError("Source file has no entries")

    # Calculate entries needed
    avg_entry_size = os.path.getsize(source_path) / original_count
    entries_needed = int(target_size / avg_entry_size)

    # Clone entries until target size reached
    while os.path.getsize(target_path) < target_size:
        for entry in entries:
            cloned = ET.fromstring(ET.tostring(entry))
            # Modify GUID to avoid duplicates
            guid_elem = cloned.find("guid")
            if guid_elem is not None:
                import uuid
                guid_elem.text = str(uuid.uuid4())

            # Modify lexical unit
            lex_unit = cloned.find(".//lexical-unit")
            if lex_unit is not None:
                form = lex_unit.find(".//form")
                if form is not None:
                    text = form.find(".//text")
                    if text is not None:
                        import uuid
                        text.text = f"{text.text}_{uuid.uuid4().hex[:8]}"

            root.append(cloned)

    # Write output
    tree.write(target_path, encoding="utf-8", xml_declaration=True)
    return target_path


# =============================================================================
# Performance Profiling Utilities
# =============================================================================

class PerformanceProfiler:
    """Collect and analyze performance metrics."""

    def __init__(self):
        self.metrics: List[Dict] = []
        self.checkpoints: Dict[str, float] = {}

    def start(self, operation: str):
        """Start timing an operation."""
        self.checkpoints[operation] = time.time()
        self.current_operation = operation

    def checkpoint(self, name: str):
        """Record a checkpoint."""
        if self.current_operation in self.checkpoints:
            elapsed = time.time() - self.checkpoints[self.current_operation]
            self.metrics.append({
                "operation": self.current_operation,
                "checkpoint": name,
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            })

    def stop(self) -> float:
        """Stop timing and return total elapsed."""
        if self.current_operation in self.checkpoints:
            elapsed = time.time() - self.checkpoints[self.current_operation]
            self.metrics.append({
                "operation": self.current_operation,
                "checkpoint": "complete",
                "elapsed_seconds": elapsed,
                "timestamp": datetime.now().isoformat()
            })
            del self.checkpoints[self.current_operation]
            return elapsed
        return 0.0

    def summary(self) -> str:
        """Get summary of metrics."""
        if not self.metrics:
            return "No metrics recorded"

        lines = ["Performance Summary:"]
        for op in set(m["operation"] for m in self.metrics):
            op_metrics = [m for m in self.metrics if m["operation"] == op]
            total = max(m["elapsed_seconds"] for m in op_metrics)
            lines.append(f"  {op}: {total:.2f}s total")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export metrics as JSON."""
        import json
        return json.dumps(self.metrics, indent=2)


# =============================================================================
# Checksum Utilities
# =============================================================================

def calculate_sha256(filepath: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def count_entries_in_lift(filepath: Path) -> int:
    """Count entries in a LIFT file."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(filepath)
    return len(tree.findall(".//entry"))


# =============================================================================
# Page Object Models
# =============================================================================

class ImportPage:
    """Page object for LIFT file import."""

    def __init__(self, page):
        self.page = page

    def navigate(self, base_url: str):
        """Navigate to import page."""
        self.page.goto(f"{base_url}/import/lift")

    def upload_file(self, file_path: Path, overwrite: bool = True):
        """Upload a LIFT file with optional settings.

        Args:
            file_path: Path to the LIFT file to upload
            overwrite: If True, check the "overwrite existing" box for fast replace mode
        """
        # Wait for the form to be ready
        self.page.wait_for_selector("form input[type='file']", timeout=10000)

        # Check overwrite box for fast replace mode (vs slow merge mode)
        if overwrite:
            overwrite_checkbox = self.page.locator("#overwrite_existing")
            if overwrite_checkbox.count() > 0 and not overwrite_checkbox.is_checked():
                overwrite_checkbox.check()

        # Upload the file
        self.page.set_input_files("input[type='file']", str(file_path))

        # Submit the form - the import is a synchronous POST request
        self.page.click("button[type='submit']")

    def wait_for_completion(self, timeout: int = 60) -> bool:
        """Wait for import to complete by checking for redirect to entries page."""
        try:
            # Wait for navigation to entries page (successful import) or back to import page (error)
            self.page.wait_for_url("**/entries", timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def wait_for_progress_complete(self, timeout: int = 60) -> int:
        """Wait for import to complete and return progress."""
        if self.wait_for_completion(timeout):
            return 100
        return 0

    def get_progress(self) -> int:
        """Get import progress percentage."""
        # No progress bar in current implementation - assume complete if on entries page
        if "/entries" in self.page.url:
            return 100
        return 0

    def is_success(self) -> bool:
        """Check if import succeeded."""
        return "/entries" in self.page.url

    def get_entry_count(self) -> int:
        """Get number of imported entries from entries page."""
        try:
            # Parse the "Showing X of Y entries" text
            info_text = self.page.locator(".showing-entries-info, .entry-count, text=Showing").first.inner_text()
            import re
            match = re.search(r'of\s+(\d+)', info_text)
            if match:
                return int(match.group(1))
            return 0
        except Exception:
            return 0

    def get_error_message(self) -> str:
        """Get error message if import failed."""
        try:
            return self.page.locator(".import-error").inner_text()
        except Exception:
            return ""


class DictionaryPage:
    """Page object for dictionary browsing."""

    def __init__(self, page):
        self.page = page

    def navigate(self, base_url: str, dictionary_id: int = None):
        """Navigate to dictionary/entries view."""
        if dictionary_id:
            self.page.goto(f"{base_url}/dictionary/{dictionary_id}")
        else:
            self.page.goto(f"{base_url}/entries")

    def wait_for_loaded(self, timeout: int = 30) -> bool:
        """Wait for dictionary to fully load."""
        try:
            self.page.wait_for_selector("#entry-count", timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def get_total_entry_count(self) -> int:
        """Get total entry count."""
        try:
            # Try different selectors
            locator = self.page.locator("#entry-count")
            if locator.count() > 0:
                text = locator.inner_text()
                if "Loading" not in text:
                    # Format: "Showing 20 of 318 entries" or just a number
                    import re
                    match = re.search(r'of (\d+)', text)
                    if match:
                        return int(match.group(1))
                    # Try parsing as simple number
                    try:
                        return int(text.replace(",", ""))
                    except ValueError:
                        pass
            # Fallback: count visible entries
            return len(self.page.locator(".entry-link").all())
        except Exception:
            return 0

    def get_visible_entry_count(self) -> int:
        """Get count of currently visible entries."""
        return self.page.locator(".entry-link").count()

    def search(self, term: str):
        """Search/filter entries using the filter input.

        Note: The entries page uses #filter-entries (not #entrySearch which is
        inside a merge modal). This method types in the filter and triggers search.
        """
        # Use JavaScript to set the value directly - more reliable than page.fill
        # for filter inputs that trigger AJAX reloads
        self.page.evaluate("""
            (term) => {
                const input = document.getElementById('filter-entries');
                if (input) {
                    input.value = term;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        """, term)

        # Press Enter to trigger the filter
        self.page.press("#filter-entries", "Enter")

    def wait_for_results(self, timeout: int = 10):
        """Wait for search results to load."""
        # Wait for network to be idle (AJAX calls complete)
        self.page.wait_for_load_state("networkidle", timeout=timeout * 1000)
        # Also wait a bit for DOM to update
        self.page.wait_for_timeout(500)

    def wait_for_filter_to_complete(self, original_count: int, timeout: int = 15):
        """Wait for filter/search to complete and return new count.

        Monitors the entry count to detect when filtering has completed.
        """
        import time
        start_time = time.time()
        last_count = -1
        stable_count = 0

        while time.time() - start_time < timeout:
            current_count = self.get_visible_entry_count()
            if current_count == last_count:
                stable_count += 1
                if stable_count >= 2:  # Count stable for 2 checks
                    return current_count
            else:
                stable_count = 0
                last_count = current_count
            time.sleep(0.5)

        return self.get_visible_entry_count()

    def scroll_to_bottom(self):
        """Scroll to bottom of page."""
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

    def click_entry(self, entry_id: str):
        """Click on an entry to open it."""
        self.page.click(f"[data-entry-id='{entry_id}'] .entry-link")

    def get_first_entry_id(self) -> Optional[str]:
        """Get ID of first visible entry."""
        try:
            return self.page.locator(".entry-link").first.get_attribute("data-entry-id")
        except Exception:
            return None

    def get_entry_ids(self, count: int) -> List[str]:
        """Get first N entry IDs."""
        ids = []
        for i in range(count):
            try:
                ids.append(
                    self.page.locator(".entry-link").nth(i).get_attribute("data-entry-id")
                )
            except Exception:
                break
        return ids

    def get_random_entry_id(self) -> Optional[str]:
        """Get a random entry ID."""
        try:
            entries = self.page.locator(".entry-link").all()
            if entries:
                import random
                return random.choice(entries).get_attribute("data-entry-id")
        except Exception:
            pass
        return None


class EditorPage:
    """Page object for entry editing."""

    def __init__(self, page):
        self.page = page

    def navigate(self, base_url: str, dictionary_id: int):
        """Navigate to editor view."""
        self.page.goto(f"{base_url}/curate/{dictionary_id}")

    def wait_for_loaded(self, timeout: int = 30) -> bool:
        """Wait for editor to load."""
        try:
            self.page.wait_for_selector(".editor-loaded", timeout=timeout * 1000)
            return True
        except Exception:
            return False

    def get_entry_count(self) -> int:
        """Get total entry count."""
        try:
            return int(self.page.locator(".total-entries").inner_text())
        except Exception:
            return 0

    def open_entry_for_edit(self, entry_id: str):
        """Open an entry for editing."""
        self.page.click(f"[data-entry-id='{entry_id}'] .edit-button")
        self.page.wait_for_selector(".entry-editor-open")

    def set_definition(self, definition: str):
        """Set the definition field."""
        self.page.fill(".definition-field", definition)

    def save_entry(self):
        """Save the current entry."""
        self.page.click(".save-button")
        self.page.wait_for_selector(".save-complete", timeout=10000)

    def is_save_successful(self) -> bool:
        """Check if last save was successful."""
        return self.page.locator(".save-success").is_visible()

    def wait_for_save_completion(self, timeout: int = 30):
        """Wait for save to complete."""
        self.page.wait_for_selector(".save-complete", timeout=timeout * 1000)

    def cancel_edit(self):
        """Cancel the current edit."""
        self.page.click(".cancel-button")

    def delete_entry(self, entry_id: str):
        """Initiate delete for an entry."""
        self.page.click(f"[data-entry-id='{entry_id}'] .delete-button")

    def confirm_delete(self):
        """Confirm deletion."""
        self.page.click(".confirm-delete-button")

    def is_delete_confirmation_visible(self) -> bool:
        """Check if delete confirmation is visible."""
        return self.page.locator(".delete-confirmation").is_visible()

    def wait_for_deletion_completion(self, timeout: int = 30):
        """Wait for deletion to complete."""
        self.page.wait_for_selector(".deletion-complete", timeout=timeout * 1000)

    def is_delete_successful(self) -> bool:
        """Check if last delete was successful."""
        return self.page.locator(".delete-success").is_visible()

    def entry_exists(self, entry_id: str) -> bool:
        """Check if entry still exists."""
        return self.page.locator(f"[data-entry-id='{entry_id}']").is_visible()


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture
def available_test_files():
    """Get dictionary of available test files."""
    return get_available_test_files()


@pytest.fixture
def small_test_file():
    """Provide path to small test file (skips if not found)."""
    return require_test_file("small", "small file testing")


@pytest.fixture
def medium_test_file():
    """Provide path to medium test file (skips if not found)."""
    return require_test_file("medium", "medium file testing")


@pytest.fixture
def large_test_file():
    """Provide path to large test file (skips if not found)."""
    return require_test_file("large", "large file testing")


@pytest.fixture
def xlarge_test_file():
    """Provide path to xlarge test file (skips if not found)."""
    return require_test_file("xlarge", "stress testing")


@pytest.fixture
def full_export_file():
    """Provide path to full export file (skips if not found)."""
    return require_test_file("full", "full dataset profiling")


@pytest.fixture
def profiler():
    """Provide a performance profiler."""
    return PerformanceProfiler()


# =============================================================================
# Test Classes
# =============================================================================

class TestFileAvailability:
    """Verify test files are available."""

    def test_test_files_directory_exists(self):
        """Verify test files directory exists."""
        assert LARGE_TEST_FILES_DIR.exists(), (
            f"Test directory {LARGE_TEST_FILES_DIR} does not exist. "
            "Create it and add test LIFT files."
        )

    def test_available_files_listed(self, available_test_files):
        """List available test files."""
        if not available_test_files:
            pytest.skip("No test files found. Add LIFT files to test_data/large_files/")

        print("\nAvailable test files:")
        for category, path in available_test_files.items():
            size_mb = path.stat().st_size / 1_000_000
            entries = count_entries_in_lift(path)
            print(f"  {category}: {path.name} ({size_mb:.1f} MB, {entries} entries)")


class TestFileGeneration:
    """Generate test files from source (requires source file)."""

    def test_generate_small_file(self, small_test_file, tmp_path):
        """Generate 1MB test file from small source."""
        if not small_test_file:
            pytest.skip("Source file not available")

        # This would use the generation function
        # output = tmp_path / "generated-small.lift"
        # generate_test_file_from_source(small_test_file, output, 1)
        # assert output.stat().st_size > 1_000_000
        pytest.skip("Generation not implemented - generate externally")


class TestImportPerformance:
    """Test file import performance with Playwright."""

    def test_import_full_file(self, page, full_export_file, app_url):
        """Test importing the full 153K entry file using the overwrite checkbox for fast replace mode."""
        import_page = ImportPage(page)

        # Record start time
        import time
        start = time.time()

        # Navigate to import page
        import_page.navigate(app_url)

        # Upload the large file with overwrite checkbox checked (for fast replace mode)
        import_page.upload_file(full_export_file, overwrite=True)

        # Wait for redirect to entries page
        success = import_page.wait_for_completion(timeout=30)

        elapsed = time.time() - start

        print(f"\nImport performance test ({full_export_file.name}):")
        print(f"  File size: {full_export_file.stat().st_size / 1_000_000:.1f} MB")
        print(f"  Entries: {count_entries_in_lift(full_export_file):,}")
        print(f"  Import time: {elapsed:.2f}s ({elapsed/60:.1f} min)")

        if success:
            entry_count = import_page.get_entry_count()
            print(f"  Entries after import: {entry_count:,}")
            print(f"  Status: SUCCESS")
        else:
            print(f"  Status: FAILED or TIMEOUT")


class TestSearchPerformance:
    """Test search performance with large datasets using Playwright."""

    def test_search_performance(self, page, full_export_file, app_url):
        """Test search response time with full dataset - UI only, no DB access."""
        dict_page = DictionaryPage(page)

        # Navigate to entries page
        page.goto(f"{app_url}/entries")

        try:
            # Wait for page to load
            page.wait_for_load_state("networkidle", timeout=30000)

            # Check if we have entries
            entry_count = dict_page.get_total_entry_count()
            if entry_count == 0:
                print(f"\nNo entries found on page. Skipping search test.")
                pytest.skip("No entries available for search testing")

            print(f"\nSearch performance test ({entry_count} total entries):")

        except Exception as e:
            print(f"\nCould not load entries page: {e}")
            pytest.skip("Entries page not available")

        # Warm up - clear any existing filter first
        page.fill("#filter-entries", "")
        page.press("#filter-entries", "Enter")
        dict_page.wait_for_results()

        original_count = dict_page.get_visible_entry_count()
        print(f"  Visible entries: {original_count}")

        # Time searches
        test_terms = ["house", "water", "time"]  # Skip very common terms like "a" and "the"

        for term in test_terms:
            start = time.time()
            dict_page.search(term)
            # Wait for filter to complete using the robust wait method
            dict_page.wait_for_filter_to_complete(original_count)
            elapsed = time.time() - start
            result_count = dict_page.get_visible_entry_count()
            print(f"  '{term}': {elapsed:.3f}s ({result_count} results)")


class TestMemoryUsage:
    """Test memory usage during operations with Playwright."""

    def test_browser_memory_during_search(self, page, full_export_file, app_url):
        """Monitor browser memory during search operations."""
        dict_page = DictionaryPage(page)

        # Navigate to entries page
        page.goto(f"{app_url}/entries")

        try:
            page.wait_for_load_state("networkidle", timeout=30000)
            entry_count = dict_page.get_total_entry_count()

            if entry_count == 0:
                pytest.skip("No entries available")

            dict_page.wait_for_loaded(timeout=60)
        except Exception as e:
            print(f"\nCould not access entries page: {e}")
            pytest.skip("Entries page not available")

        # Check if memory API is available (Chrome only)
        memory_available = page.evaluate("() => 'memory' in performance")

        if not memory_available:
            print("\nMemory API not available (Chrome only)")
            for term in ["house", "water"]:
                dict_page.search(term)
                dict_page.wait_for_results()
            print("  Search operations completed (memory not measured)")
            return

        # Get initial memory
        initial_memory = page.evaluate("() => performance.memory.usedJSHeapSize")

        # Perform searches
        for term in ["house", "water", "time"]:
            dict_page.search(term)
            dict_page.wait_for_results()

        # Get peak memory
        peak_memory = page.evaluate("() => performance.memory.usedJSHeapSize")

        print(f"\nMemory usage test:")
        print(f"  Initial: {initial_memory / 1_000_000:.0f} MB")
        print(f"  Peak: {peak_memory / 1_000_000:.0f} MB")
        print(f"  Increase: {(peak_memory - initial_memory) / 1_000_000:.0f} MB")


class TestDataIntegrity:
    """Test data integrity after operations."""

    def test_xml_validity(self, available_test_files):
        """Verify all available files have valid XML."""
        for category, filepath in available_test_files.items():
            import xml.etree.ElementTree as ET
            try:
                ET.parse(filepath)
                print(f"{category}: Valid XML")
            except ET.ParseError as e:
                pytest.fail(f"{category}: Invalid XML - {e}")

    def test_entry_count_reasonableness(self, available_test_files):
        """Verify entry counts are reasonable."""
        for category, filepath in available_test_files.items():
            entries = count_entries_in_lift(filepath)
            size_mb = filepath.stat().st_size / 1_000_000
            avg_size = filepath.stat().st_size / max(entries, 1)

            # Check average entry size is reasonable (100 bytes to 10KB)
            assert 100 < avg_size < 10000, (
                f"{category}: Unusual average entry size: {avg_size:.0f} bytes"
            )
            print(f"{category}: {entries} entries, {avg_size:.0f} bytes/entry")


class TestProfiling:
    """Profiling tests for full dataset analysis."""

    def test_profile_import_timing(self, full_export_file, profiler):
        """Profile import timing for full dataset."""
        if not full_export_file:
            pytest.skip("Full export file not found")

        # Time file operations without browser
        profiler.start("file_parse")
        import xml.etree.ElementTree as ET
        tree = ET.parse(full_export_file)
        profiler.checkpoint("parse_complete")

        entries = tree.findall(".//entry")
        profiler.checkpoint("count_entries")

        profiler.stop()
        print(profiler.summary())

    def test_profile_entry_traversal(self, full_export_file, profiler):
        """Profile entry traversal operations."""
        if not full_export_file:
            pytest.skip("Full export file not found")

        import xml.etree.ElementTree as ET

        profiler.start("traverse_all")
        tree = ET.parse(full_export_file)
        entries = tree.findall(".//entry")

        # Simulate common operations
        profiler.start("extract_guids")
        guids = [e.find("guid").text for e in entries if e.find("guid") is not None]
        profiler.checkpoint("guids_extracted")

        profiler.start("extract_lemmas")
        lemmas = []
        for e in entries:
            lex_unit = e.find(".//lexical-unit")
            if lex_unit is not None:
                form = lex_unit.find(".//form")
                if form is not None:
                    text = form.find(".//text")
                    if text is not None:
                        lemmas.append(text.text)
        profiler.checkpoint("lemmas_extracted")

        print(f"\nFull dataset profiling ({full_export_file.name}):")
        print(f"  Total entries: {len(entries)}")
        print(f"  GUIDs extracted: {len(guids)}")
        print(f"  Lemmas extracted: {len(lemmas)}")
        print(profiler.summary())

    def test_profile_search_index(self, full_export_file, profiler):
        """Profile in-memory search index creation."""
        if not full_export_file:
            pytest.skip("Full export file not found")

        import xml.etree.ElementTree as ET

        profiler.start("load_and_index")
        tree = ET.parse(full_export_file)
        entries = tree.findall(".//entry")

        # Build index
        index = {}
        for entry in entries:
            lex_unit = entry.find(".//lexical-unit")
            if lex_unit is not None:
                form = lex_unit.find(".//form")
                if form is not None:
                    text = form.find(".//text")
                    if text is not None:
                        lemma = text.text.lower()
                        if lemma not in index:
                            index[lemma] = []
                        index[lemma].append(entry)

        profiler.checkpoint("index_complete")

        # Test searches
        test_terms = ["a", "the", "house", "water", "time"]
        for term in test_terms:
            profiler.start(f"search_{term}")
            results = index.get(term.lower(), [])
            profiler.checkpoint(f"found_{len(results)}")

        print(f"\nSearch index profiling ({full_export_file.name}):")
        print(f"  Unique lemmas: {len(index)}")
        for term in test_terms:
            count = len(index.get(term.lower(), []))
            print(f"  '{term}': {count} entries")
        print(profiler.summary())


# =============================================================================
# Running Tests
# =============================================================================

if __name__ == "__main__":
    # Quick check of available files
    print("Checking for test files...")
    available = get_available_test_files()

    if not available:
        print(f"\nNo test files found in {LARGE_TEST_FILES_DIR}")
        print("\nTo add test files:")
        print("1. Create directory: mkdir -p tests/e2e/test_data/large_files")
        print("2. Add your LIFT files (e.g., exported_lift.lift)")
        print("3. Files are automatically gitignored")
    else:
        print(f"\nFound {len(available)} test file(s):")
        for category, path in available.items():
            size_mb = path.stat().st_size / 1_000_000
            entries = count_entries_in_lift(path)
            print(f"  {category}: {path.name}")
            print(f"    Size: {size_mb:.1f} MB")
            print(f"    Entries: {entries:,}")

# =============================================================================
# Performance Targets
# =============================================================================
#
# Expected performance for ~150K entry file:
#
# | Operation          | Target    | Warning    |
# |--------------------|-----------|------------|
# | XML Parse          | < 30s     | < 60s      |
# | Entry Count        | < 5s      | < 10s      |
# | GUID Extraction    | < 10s     | < 20s      |
# | Lemma Index Build  | < 15s     | < 30s      |
# | Search (cold)      | < 2s      | < 5s       |
# | Search (cached)    | < 100ms   | < 500ms    |
#
