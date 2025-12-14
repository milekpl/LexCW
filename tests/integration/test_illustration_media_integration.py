"""
Integration tests for illustration upload/delete/info endpoints.
"""

from io import BytesIO
import os
import pytest
from flask import current_app

PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
    b'\x00\x00\x00\nIDATx^c\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
)


@pytest.mark.integration
def test_image_upload_and_delete(client):
    data = {'image_file': (BytesIO(PNG_BYTES), 'test.png')}
    response = client.post('/api/illustration/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    filename = data['filename']

    # Info endpoint
    info_resp = client.get(f'/api/illustration/info/{filename}')
    assert info_resp.status_code == 200
    info = info_resp.get_json()
    assert info['success'] is True
    assert info['url'].endswith(f'/static/images/{filename}')

    # File exists on disk
    file_path = os.path.join(current_app.static_folder, 'images', filename)
    assert os.path.exists(file_path)

    # Delete
    del_resp = client.delete(f'/api/illustration/delete/{filename}')
    assert del_resp.status_code == 200
    del_data = del_resp.get_json()
    assert del_data['success'] is True
    assert not os.path.exists(file_path)
