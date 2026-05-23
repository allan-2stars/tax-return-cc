"""HTTP smoke tests for /estimator route group."""
import pytest


@pytest.mark.asyncio
async def test_summary_fields_present(auth_client):
    """GET /estimator/summary returns 200 with all expected fields."""
    resp = await auth_client.get("/api/v1/estimator/summary")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert "gross_income" in data
    assert "total_deductions" in data
    assert "taxable_income" in data
    assert "payg_withheld" in data
    assert "confirmed_only" in data
    assert "pending_count" in data
    assert "ato_calculator_url" in data
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_summary_empty_totals(auth_client):
    """GET /estimator/summary with no confirmed events returns zero totals."""
    resp = await auth_client.get("/api/v1/estimator/summary")
    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]
    assert float(data["gross_income"]) == 0.0
    assert float(data["total_deductions"]) == 0.0
    assert float(data["taxable_income"]) == 0.0
    assert float(data["payg_withheld"]) == 0.0
    assert data["confirmed_only"] is True
    assert data["pending_count"] == 0
