def test_create_project_success(client, sample_data):
    payload = {
        "name": "Project Artemis",
        "description": "Exploration initiative",
        "status": "active",
        "owner_id": sample_data["user1"].id
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Project Artemis"
    assert data["owner_id"] == sample_data["user1"].id
    assert data["task_count"] == 0

def test_create_project_invalid_owner(client):
    payload = {
        "name": "Ghost Project",
        "owner_id": 88888
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]

def test_list_projects_with_task_counts(client, sample_data):
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    proj = [p for p in data if p["id"] == sample_data["project"].id][0]
    assert proj["name"] == "Apollo Launch"
    # In sample_data, 3 tasks belong to this project
    assert proj["task_count"] == 3

def test_get_project_detail(client, sample_data):
    proj_id = sample_data["project"].id
    response = client.get(f"/api/v1/projects/{proj_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Apollo Launch"
    assert data["owner"]["email"] == "alice@example.com"
    assert data["task_count"] == 3

def test_update_project(client, sample_data):
    proj_id = sample_data["project"].id
    response = client.patch(f"/api/v1/projects/{proj_id}", json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

def test_delete_project_cascade(client, sample_data):
    proj_id = sample_data["project"].id
    del_resp = client.delete(f"/api/v1/projects/{proj_id}")
    assert del_resp.status_code == 204

    # Verify project is gone
    get_resp = client.get(f"/api/v1/projects/{proj_id}")
    assert get_resp.status_code == 404

    # Verify tasks belonging to project are also gone (cascade)
    tasks_resp = client.get(f"/api/v1/tasks?project_id={proj_id}")
    assert tasks_resp.status_code == 200
    assert len(tasks_resp.json()) == 0
