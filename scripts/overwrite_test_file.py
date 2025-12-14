from pathlib import Path


def main() -> None:
    target = Path("tests/integration/test_ranges_elements_crud.py")
    content = """import pytest

# Legacy duplicated test file. The authoritative tests live in
# `tests/integration/test_ranges_elements_crud_clean.py`.
# Keep the module skipped to avoid accidentally executing legacy code.
pytest.skip(
    "Legacy duplicated test file - replaced by tests/integration/test_ranges_elements_crud_clean.py",
    allow_module_level=True,
)
"""
    target.write_text(content)


if __name__ == "__main__":
    main()
