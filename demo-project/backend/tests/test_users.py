def test_create_user_success(client):
    payload = {
        "email": "charlie@example.com",
        "full_name": "Charlie Tester",
        "role": "member",
        "is_active": True
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "charlie@example.com"
    assert data["full_name"] == "Charlie Tester"
    assert "id" in data
    assert "created_at" in data

def test_create_user_duplicate_email(client, sample_data):
    payload = {
        "email": "alice@example.com",
        "full_name": "Alice Duplicate",
        "role": "member"
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_create_user_invalid_role(client):
    payload = {
        "email": "invalid@example.com",
        "full_name": "Invalid Role",
        "role": "superhero"  # invalid role
    }
    response = client.post("/api/v1/users", json=payload)
    assert response.status_code == 422

def test_list_users(client, sample_data):
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    emails = [u["email"] for u in data]
    assert "alice@example.com" in emails
    assert "bob@example.com" in emails

def test_get_user_by_id(client, sample_data):
    user_id = sample_data["user1"].id
    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    assert response.json()["email"] == "alice@example.com"

def test_get_user_not_found(client):
    response = client.get("/api/v1/users/99999")
    assert response.status_code == 404

def test_update_user(client, sample_data):
    user_id = sample_data["user2"].id
    update_payload = {"full_name": "Bob The Builder"}
    response = client.patch(f"/api/v1/users/{user_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["full_name"] == "Bob The Builder"
