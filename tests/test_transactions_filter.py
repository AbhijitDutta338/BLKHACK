def test_transactions_filter(client):
    payload = {
        "q": [
            {
            "fixed": 0,
            "start": "2023-07-01 00:00:00",
            "end": "2023-07-31 23:59:59"
            }
        ],
        "p": [
            {
            "extra": 30,
            "start": "2023-10-01 00:00:00",
            "end": "2023-12-31 23:59:59"
            }
        ],
        "k": [
            {
            "start": "2023-01-01 00:00:00",
            "end": "2023-12-31 23:59:59"
            }
        ],
        "wage": 50000,
        "transactions": [
            {
                "date": "2023-12-17 08:09:45",
                "amount": -10
            }
        ]
    }

    response = client.post(
        "/blackrock/challenge/v1/transactions:filter",
        json=payload
    )

    assert response.status_code == 200
    
    data = response.get_json()
    
    assert len(data["invalid"]) == 1
    assert "Negative amounts" in data["invalid"][0]["message"]