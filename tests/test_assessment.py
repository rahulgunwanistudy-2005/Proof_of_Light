import pytest
import requests
from fastapi import HTTPException

from apps.api.review.assessment import analyze


@pytest.mark.parametrize(
    ("provider_status", "message"),
    [(402, "billing or quota"), (429, "request limit")],
)
def test_unavailable_gemini_quota_reports_recoverable_error(monkeypatch, provider_status, message):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    response = requests.Response()
    response.status_code = provider_status
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: response)
    with pytest.raises(HTTPException, match=message) as error:
        analyze(b"test-image", "Test statement")
    assert error.value.status_code == 503
