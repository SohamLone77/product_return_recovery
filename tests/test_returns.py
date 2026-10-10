def test_empty_returns_list(client):
    """Test 4: Empty return lists are handled correctly."""
    response = client.get("/returns")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_create_valid_return(client):
    """Test 1: Valid return creation persists a record and returns its ID."""
    payload = {
        "product_id": "SKU-9921",
        "product_name": "Premium Noise Cancelling Headphones",
        "category": "Electronics",
        "purchase_price": 299.99,
        "currency": "USD",
        "customer_id": "CUST-1001",
        "order_id": "ORD-55421",
        "return_reason": "Ear cup cushion loose on right side",
    }
    response = client.post("/returns", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["id"].startswith("ret_")
    assert data["product_id"] == "SKU-9921"
    assert data["status"] == "registered"
    assert data["purchase_price"] == 299.99

    # Verify retrieval
    get_res = client.get("/returns")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["total"] == 1
    assert get_data["items"][0]["id"] == data["id"]


def test_create_invalid_return_payload(client):
    """Test 2: Invalid return payloads are rejected."""
    # Negative purchase price
    invalid_price = {
        "product_id": "SKU-9921",
        "product_name": "Headphones",
        "category": "Electronics",
        "purchase_price": -50.0,
        "customer_id": "CUST-1001",
        "return_reason": "Broken",
    }
    res = client.post("/returns", json=invalid_price)
    assert res.status_code == 422

    # Missing mandatory field
    missing_field = {
        "product_id": "SKU-9921",
        "purchase_price": 100.0,
    }
    res2 = client.post("/returns", json=missing_field)
    assert res2.status_code == 422


def test_pagination_and_filtering(client):
    """Test 3 & 5: GET /returns pagination and filter parameters."""
    # Create 3 returns
    items = [
        {"product_id": "SKU-1", "product_name": "Laptop Pro", "category": "Computers", "purchase_price": 1200.0, "customer_id": "C-1", "return_reason": "Defective screen"},
        {"product_id": "SKU-2", "product_name": "Smart Watch", "category": "Electronics", "purchase_price": 250.0, "customer_id": "C-2", "return_reason": "Battery issues"},
        {"product_id": "SKU-3", "product_name": "Gaming Mouse", "category": "Electronics", "purchase_price": 80.0, "customer_id": "C-3", "return_reason": "Double clicking"},
    ]
    for item in items:
        client.post("/returns", json=item)

    # Test limit and offset
    page_res = client.get("/returns?limit=2&offset=0")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["total"] == 3
    assert len(page_data["items"]) == 2
    assert page_data["limit"] == 2
    assert page_data["offset"] == 0

    page_2 = client.get("/returns?limit=2&offset=2")
    assert page_2.status_code == 200
    assert len(page_2.json()["items"]) == 1

    # Filter by category
    filter_res = client.get("/returns?category=Computers")
    assert filter_res.status_code == 200
    assert filter_res.json()["total"] == 1
    assert filter_res.json()["items"][0]["category"] == "Computers"
