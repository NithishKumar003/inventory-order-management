import pytest

import app.services as payment_services


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


def test_order_not_found(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(404)

    monkeypatch.setattr(payment_services.httpx, "get", fake_get)

    with pytest.raises(LookupError, match="Order not found"):
        payment_services.get_customer_order(
            order_id=1,
            access_token="test-token",
        )


@pytest.mark.parametrize("status_code", [401, 403])
def test_order_authentication_failure(monkeypatch, status_code):
    def fake_get(*args, **kwargs):
        return FakeResponse(status_code)

    monkeypatch.setattr(payment_services.httpx, "get", fake_get)

    with pytest.raises(PermissionError):
        payment_services.get_customer_order(
            order_id=1,
            access_token="test-token",
        )


def test_order_service_server_error(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(500)

    monkeypatch.setattr(payment_services.httpx, "get", fake_get)

    with pytest.raises(RuntimeError, match="could not validate"):
        payment_services.get_customer_order(
            order_id=1,
            access_token="test-token",
        )


def test_valid_order_response(monkeypatch):
    order_data = {
        "id": 1,
        "user_id": 7,
        "total_amount": "1250.00",
        "status": "Confirmed",
    }

    def fake_get(*args, **kwargs):
        return FakeResponse(200, order_data)

    monkeypatch.setattr(payment_services.httpx, "get", fake_get)

    result = payment_services.get_customer_order(
        order_id=1,
        access_token="test-token",
    )

    assert result == order_data
