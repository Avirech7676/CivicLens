import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.db.session import Base, get_db, engine as prod_engine

TestingSessionLocal = lambda: Session(bind=prod_engine)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=prod_engine)
    Base.metadata.create_all(bind=prod_engine)
    yield
    Base.metadata.drop_all(bind=prod_engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_1_valid_jpeg_upload():
    # Valid JPEG header: \xFF\xD8\xFF\xE0
    jpeg_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xFF\xDB"
    res = client.post(
        "/api/v1/reports",
        data={"description": "Valid JPEG evidence report test"},
        files={"file": ("photo.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["image_path"] is not None
    assert data["image_path"].startswith("/uploads/")


def test_2_valid_png_upload():
    # Valid PNG header: \x89PNG\r\n\x1a\n
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    res = client.post(
        "/api/v1/reports",
        data={"description": "Valid PNG evidence report test"},
        files={"file": ("evidence.png", io.BytesIO(png_bytes), "image/png")}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["image_path"] is not None
    assert data["image_path"].endswith(".png")


def test_3_invalid_extension_upload():
    txt_bytes = b"Hello world text file"
    res = client.post(
        "/api/v1/reports",
        data={"description": "Invalid extension upload test"},
        files={"file": ("malicious.exe", io.BytesIO(txt_bytes), "application/octet-stream")}
    )
    assert res.status_code == 400
    assert "Invalid file extension" in res.json()["detail"]


def test_4_fake_image_extension_with_non_image_content():
    # Renamed text/script file named fake_photo.jpg containing non-image text
    fake_bytes = b"<?php echo 'malicious script'; ?>"
    res = client.post(
        "/api/v1/reports",
        data={"description": "Fake image extension test"},
        files={"file": ("fake_photo.jpg", io.BytesIO(fake_bytes), "image/jpeg")}
    )
    assert res.status_code == 400
    assert "signature validation failed" in res.json()["detail"]


def test_5_oversized_file_upload():
    # Generate 10.5 MB file (over 10MB limit)
    large_bytes = b"\xFF\xD8\xFF\xE0" + b"0" * (10 * 1024 * 1024 + 500)
    res = client.post(
        "/api/v1/reports",
        data={"description": "Oversized upload test"},
        files={"file": ("big_photo.jpg", io.BytesIO(large_bytes), "image/jpeg")}
    )
    assert res.status_code == 400
    assert "exceeds maximum allowed limit" in res.json()["detail"]


def test_6_path_traversal_filename_upload():
    jpeg_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01"
    res = client.post(
        "/api/v1/reports",
        data={"description": "Path traversal filename test"},
        files={"file": ("../../../../etc/passwd.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    )
    assert res.status_code == 201
    data = res.json()
    # Path traversal characters must be sanitized, storing file safely in /uploads/
    assert "../" not in data["image_path"]
    assert data["image_path"].startswith("/uploads/")
