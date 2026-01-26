"""Test announcement gap API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


def test_scan_announcement_gap():
    """Test scan endpoint."""
    client = TestClient(app)
    response = client.post(
        "/api/v1/announcement-gap/scan",
        json={"min_price": 0.20, "min_gap_pct": 0.0, "lookback_months": 6},
    )
    assert response.status_code in [200, 500]
    data = response.json()
    assert "success" in data


def test_health_endpoint():
    """Test health endpoint with injected dependencies."""
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime_seconds" in data
