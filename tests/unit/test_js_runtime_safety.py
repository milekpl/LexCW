import os
import subprocess
import tempfile
import pytest


def _run_node_script(script_content: str) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tf:
        tf.write(script_content)
        temp_path = tf.name

    try:
        return subprocess.run(['node', temp_path], capture_output=True, text=True, timeout=10)
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


def test_node_shim_allows_require_of_entry_form():
    """Requiring the entry-form module under Node with our shim should not throw."""
    shim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'js_node_shim.js'))
    entry_form_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static', 'js', 'entry-form.js'))

    script = f"""
    // Load shim and require the module
    require('{shim_path}');
    // Allow modules to use console
    global.console = console;
    require('{entry_form_path}');
    console.log('ENTRY_OK');
    """

    result = _run_node_script(script)
    assert result.returncode == 0, f"Entry form require failed: {result.stderr}"
    assert 'ENTRY_OK' in result.stdout


def test_node_shim_allows_require_of_pronunciation_forms():
    """Requiring pronunciation-forms should not throw under the Node shim."""
    shim_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'js_node_shim.js'))
    pron_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app', 'static', 'js', 'pronunciation-forms.js'))

    script = f"""
    require('{shim_path}');
    global.console = console;
    require('{pron_path}');
    console.log('PRON_OK');
    """

    result = _run_node_script(script)
    assert result.returncode == 0, f"Pronunciation forms require failed: {result.stderr}"
    assert 'PRON_OK' in result.stdout
