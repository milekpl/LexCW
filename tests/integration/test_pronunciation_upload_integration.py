"""
Integration tests for pronunciation audio upload/delete/info API endpoints.

Tests the backend API for audio file upload functionality used by the entry form.
"""

from io import BytesIO
import os
import pytest
from flask import current_app

# Minimal valid MP3 bytes (not a real MP3, but passes basic validation)
MP3_BYTES = b'\xff\xfb\x90\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


@pytest.mark.integration
def test_audio_upload_requires_ipa(client):
    """Audio upload should fail if IPA transcription is not provided."""
    data = {'audio_file': (BytesIO(MP3_BYTES), 'test.mp3')}
    response = client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'IPA' in data['message']


@pytest.mark.integration
def test_audio_upload_and_delete(client):
    """Test complete audio upload, info, and delete flow."""
    # Upload audio with IPA
    data = {
        'audio_file': (BytesIO(MP3_BYTES), 'test.mp3'),
        'ipa_value': '/ˈtest/',
        'index': '0'
    }
    response = client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')
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

    # Info endpoint
    info_resp = client.get(f'/api/pronunciation/info/{filename}')
    assert info_resp.status_code == 200
    info = info_resp.get_json()
    assert info['success'] is True
    assert info['url'].endswith(f'/static/audio/{filename}')

    # File exists on disk
    file_path = os.path.join(current_app.static_folder, 'audio', filename)
    assert os.path.exists(file_path)

    # Delete
    del_resp = client.delete(f'/api/pronunciation/delete/{filename}')
    assert del_resp.status_code == 200
    del_data = del_resp.get_json()
    assert del_data['success'] is True
    assert not os.path.exists(file_path)


@pytest.mark.integration
def test_audio_upload_with_different_formats(client):
    """Test uploading audio in different formats."""
    formats = ['wav', 'ogg', 'opus', 'm4a']

    for fmt in formats:
        data = {
            'audio_file': (BytesIO(MP3_BYTES), f'test.{fmt}'),
            'ipa_value': f'/test-{fmt}/',
            'index': '0'
        }
        response = client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')
        assert response.status_code == 200, f"Failed for format: {fmt}"
        result = response.get_json()
        assert result['success'] is True

        # Cleanup
        client.delete(f'/api/pronunciation/delete/{result["filename"]}')


@pytest.mark.integration
def test_audio_upload_invalid_file_type(client):
    """Test that non-audio files are rejected."""
    data = {
        'audio_file': (BytesIO(b'not audio'), 'test.txt'),
        'ipa_value': '/test/',
        'index': '0'
    }
    response = client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'type' in data['message'].lower() or 'allowed' in data['message'].lower()


@pytest.mark.integration
def test_audio_upload_no_file(client):
    """Test that request without file is rejected."""
    data = {'ipa_value': '/test/', 'index': '0'}
    response = client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'file' in data['message'].lower()


@pytest.mark.integration
def test_audio_delete_nonexistent_file(client):
    """Test deleting a file that doesn't exist."""
    response = client.delete('/api/pronunciation/delete/nonexistent_file.mp3')
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
def test_audio_filename_security(client):
    """Test that directory traversal in filenames is sanitized (not rejected)."""
    # Path traversal is sanitized by secure_filename, not rejected
    # File is saved with sanitized name (e.g., "etc_passwd.mp3") in static/audio/
    data = {
        'audio_file': (BytesIO(MP3_BYTES), '../../../etc/passwd.mp3'),
        'ipa_value': '/test/',
        'index': '0'
    }
    response = client.post('/api/pronunciation/upload', data=data, content_type='multipart/form-data')
    # secure_filename converts "../../../etc/passwd.mp3" to "etc_passwd.mp3"
    # which is a valid filename, so upload succeeds
    assert response.status_code == 200
    result = response.get_json()
    assert result['success'] is True
    # Verify the sanitized filename doesn't contain path traversal
    assert '..' not in result['filename']
    assert result['filename'].startswith('/') is False

    # Cleanup
    client.delete(f'/api/pronunciation/delete/{result["filename"]}')
