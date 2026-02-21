def test_performance_endpoint(client):
    response = client.get("/blackrock/challenge/v1/performance")
    
    assert response.status_code == 200
    
    data = response.get_json()
    
    assert "memory" in data
    assert "threads" in data
    assert "time" in data
    
    assert isinstance(data["threads"], int)
    assert "MB" in data["memory"]