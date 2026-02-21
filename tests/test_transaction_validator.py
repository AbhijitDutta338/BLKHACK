def test_transactions_validator(client):
    payload = {
        "wage": 50000,
        "transactions": [
            {
                "date": "2024-03-16 10:30:00",
                "amount": 1500000.75,
                "ceiling": 200.0,
                "remanent": 49.25
            }
        ]
    }

    response = client.post(
        "/blackrock/challenge/v1/transactions:validator",
        json=payload
    )

    assert response.status_code == 200
    
    data = response.get_json()
    
    assert len(data["invalid"]) == 1
    assert data["invalid"][0]["amount"] == 1500000.75
    assert "must be >=" in data["invalid"][0]["message"]
    assert len(data["valid"]) == 0