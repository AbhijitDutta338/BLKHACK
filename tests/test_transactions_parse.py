from flask.testing import FlaskClient


def test_transactions_parse(client: FlaskClient):
    payload = [
        {
            "date": "2024-03-15 10:30:00",
            "amount": 150.75
        }
    ]

    response = client.post(
        "/blackrock/challenge/v1/transactions:parse",
        json=payload
    )

    assert response.status_code == 200
    
    data = response.get_json()
    
    assert len(data) == 1
    assert data[0]["amount"] == 150.75
    assert "ceiling" in data[0]
    assert "remanent" in data[0]