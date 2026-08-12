"""
Integration tests for pronunciation audio upload/delete/info API endpoints.

Tests the backend API for audio file upload functionality used by the entry form.

Upload and delete are authenticated (``@_require_auth("pronunciation:write")``);
info is read-only and open. Files live in the configured audio storage
(``AUDIO_STORAGE_PATH/<project_db>/``) and are served from ``/audio/...``.
"""

from io import BytesIO
import os
import pytest
from flask import current_app
from unittest.mock import MagicMock, patch

# Minimal valid MP3 bytes (not a real MP3, but passes basic validation)
MP3_BYTES = b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


@pytest.fixture
def authed_client(client):
    """Client with a mocked session user (required by the auth decorators)."""
    dummy_user = MagicMock()
    dummy_user.id = 1
    dummy_user.username = "tester"
    dummy_user.is_admin = True
    with patch("app.utils.auth_decorators.get_current_user", return_value=dummy_user):
        yield client


def _upload(client, filename="test.mp3", ipa="/ˈtest/", index="0", data_bytes=MP3_BYTES):
    data = {
        'audio_file': (BytesIO(data_bytes), filename),
        'ipa_value': ipa,
        'index': index,
    }
    return client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')


@pytest.mark.integration
def test_audio_upload_requires_auth(anonymous_client):
    """Audio upload must be rejected without a session user."""
    response = _upload(anonymous_client, ipa='')
    assert response.status_code == 401


@pytest.mark.integration
def test_audio_delete_requires_auth(anonymous_client):
    """Audio delete must be rejected without a session user."""
    response = anonymous_client.delete('/api/pronunciation/delete/whatever.mp3')
    assert response.status_code == 401


@pytest.mark.integration
def test_audio_upload_requires_ipa(authed_client):
    """Audio upload should fail if IPA transcription is not provided."""
    data = {'audio_file': (BytesIO(MP3_BYTES), 'test.mp3')}
    response = authed_client.post(
        '/api/pronunciation/upload', data=data, content_type='multipart/form-data'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'IPA' in data['message']


@pytest.mark.integration
def test_audio_upload_and_delete(authed_client):
    """Test complete audio upload, info, and delete flow."""
    from app.services.tts import audio_storage

    project_db = os.environ.get('TEST_DB_NAME') or 'dictionary'

    # Upload audio with IPA
    response = _upload(authed_client)
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    filename = data['filename']
    assert data['ipa_value'] == '/ˈtest/'
    assert data['index'] == '0'

    # Verify filename has UUID prefix
    parts = filename.split('_')
    assert len(parts) >= 2
    assert len(parts[0]) == 32  # UUID hex

    # File exists in the configured audio storage (per-project dir)
    saved_path = audio_storage.resolve_audio_path(filename, project_db)
    assert saved_path is not None and saved_path.is_file()

    # Info endpoint
    info_resp = authed_client.get(f'/api/pronunciation/info/{filename}')
    assert info_resp.status_code == 200
    info = info_resp.get_json()
    assert info['success'] is True
    assert info['url'].endswith(f'/audio/{filename}')

    # Delete
    del_resp = authed_client.delete(f'/api/pronunciation/delete/{filename}')
    assert del_resp.status_code == 200
    del_data = del_resp.get_json()
    assert del_data['success'] is True
    assert not saved_path.exists()


@pytest.mark.integration
def test_audio_upload_with_different_formats(authed_client):
    """Test uploading audio in different formats."""
    formats = ['wav', 'ogg', 'opus', 'm4a']

    for fmt in formats:
        response = _upload(authed_client, filename=f'test.{fmt}', ipa=f'/test-{fmt}/')
        assert response.status_code == 200, f"Failed for format: {fmt}"
        result = response.get_json()
        assert result['success'] is True

        # Cleanup
        authed_client.delete(f'/api/pronunciation/delete/{result["filename"]}')


@pytest.mark.integration
def test_audio_upload_invalid_file_type(authed_client):
    """Test that non-audio files are rejected."""
    response = _upload(authed_client, filename='test.txt', data_bytes=b'not audio')
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'type' in data['message'].lower() or 'allowed' in data['message'].lower()


@pytest.mark.integration
def test_audio_upload_no_file(authed_client):
    """Test that request without file is rejected."""
    data = {'ipa_value': '/test/', 'index': '0'}
    response = authed_client.post(
        '/api/pronunciation/upload', data=data, content_type='multipart/form-data'
    )
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'file' in data['message'].lower()


@pytest.mark.integration
def test_audio_delete_nonexistent_file(authed_client):
    """Test deleting a file that doesn't exist."""
    response = authed_client.delete('/api/pronunciation/delete/nonexistent_file.mp3')
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert 'not found' in data['message'].lower()


@pytest.mark.integration
def test_audio_info_nonexistent_file(client):
    """Test getting info for a file that doesn't exist."""
    response = client.get('/api/pronunciation/info/nonexistent_file.mp3')
    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False
    assert 'not found' in data['message'].lower()


@pytest.mark.integration
def test_audio_filename_security(authed_client):
    """Test that path traversal in filenames cannot escape the storage root."""
    # The uploaded name is a generated UUID-based filename (never the raw client
    # name), so traversal cannot appear in the stored filename.
    response = _upload(authed_client, filename='../../../etc/passwd.mp3')
    assert response.status_code == 200
    result = response.get_json()
    assert result['success'] is True
    assert '..' not in result['filename']
    assert result['filename'].startswith('/') is False

    # Cleanup
    authed_client.delete(f'/api/pronunciation/delete/{result["filename"]}')
