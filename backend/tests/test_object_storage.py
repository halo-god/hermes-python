"""Verify the S3/MinIO storage code path with a mocked S3 (moto).

Proves put/get/bucket-creation work without a live MinIO server. In production
the same boto3 client targets the MinIO endpoint (S3-compatible).
"""
from __future__ import annotations

import pytest

moto = pytest.importorskip("moto")
from moto import mock_aws  # noqa: E402

from app.config import settings  # noqa: E402
from app.core import object_storage  # noqa: E402


@mock_aws
def test_object_storage_roundtrip():
    # Empty endpoint → default AWS endpoint so moto intercepts the calls.
    prev_endpoint = settings.minio_endpoint
    prev_bucket = settings.minio_bucket
    settings.minio_endpoint = ""
    settings.minio_bucket = "hermes-test-bucket"
    object_storage.reset_client()
    try:
        key = "conv-1/会议纪要.md"
        body = "# 纪要\n- [x] done\n".encode("utf-8")
        returned = object_storage.put(key, body, "text/markdown")
        assert returned == key
        assert object_storage.get(key) == body
        url = object_storage.presigned_url(key)
        assert "hermes-test-bucket" in url
    finally:
        settings.minio_endpoint = prev_endpoint
        settings.minio_bucket = prev_bucket
        object_storage.reset_client()
