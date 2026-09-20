def test_create_task_success(client, sample_data):
    payload = {
        "title": "Write integration tests",
        "description": "Ensure API endpoints return 200",
        "status": "todo",
        "priority": "high",
        "project_id": sample_data["project"].id,
        "assignee_id": sample_data["user2"].id
    }
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Write integration tests"
    assert data["project_name"] == "Apollo Launch"
    assert data["comment_count"] == 0

def test_create_task_invalid_project(client):
    payload = {
        "title": "Invalid project task",
        "project_id": 99999
    }
    response = client.post("/api/v1/tasks", json=payload)
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]

def test_list_tasks(client, sample_data):
    response = client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3

def test_filter_tasks_by_status(client, sample_data):
    response = client.get("/api/v1/tasks?status=in_progress")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Implement authentication"

def test_filter_tasks_by_priority(client, sample_data):
    response = client.get("/api/v1/tasks?priority=high")
    assert response.status_code == 200
    data = response.json()
    assert all(t["priority"] == "high" for t in data)

def test_filter_tasks_by_project(client, sample_data):
    proj_id = sample_data["project"].id
    response = client.get(f"/api/v1/tasks?project_id={proj_id}")
    assert response.status_code == 200
    assert len(response.json()) == 3

def test_search_tasks(client, sample_data):
    response = client.get("/api/v1/tasks?search=authentication")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "authentication" in data[0]["title"].lower()

def test_search_tasks_matches_all_words_across_title_and_description(client, sample_data):
    response = client.get("/api/v1/tasks?search=implement%20jwt")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Implement authentication"

def test_search_tasks_ignores_extra_whitespace_and_case(client, sample_data):
    response = client.get("/api/v1/tasks?search=%20%20IMPLEMENT%20%20jwt%20")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Implement authentication"

def test_search_tasks_requires_all_words(client, sample_data):
    response = client.get("/api/v1/tasks?search=authentication%20staging")
    assert response.status_code == 200
    assert response.json() == []

def test_get_task_detail_with_comments(client, sample_data):
    task_id = sample_data["task1"].id
    response = client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert len(data["comments"]) == 1
    assert data["comments"][0]["content"] == "Started working on JWT verification."

def test_update_task(client, sample_data):
    task_id = sample_data["task1"].id
    response = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert response.status_code == 200
    assert response.json()["status"] == "done"

def test_delete_task(client, sample_data):
    task_id = sample_data["task3"].id
    del_resp = client.delete(f"/api/v1/tasks/{task_id}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/v1/tasks/{task_id}")
    assert get_resp.status_code == 404
