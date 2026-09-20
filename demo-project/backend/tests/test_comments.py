def test_add_comment_success(client, sample_data):
    task_id = sample_data["task1"].id
    user_id = sample_data["user1"].id
    payload = {
        "content": "Reviewed initial commit, looking great!",
        "author_id": user_id
    }
    response = client.post(f"/api/v1/tasks/{task_id}/comments", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "Reviewed initial commit, looking great!"
    assert data["task_id"] == task_id
    assert data["author_id"] == user_id

def test_add_comment_nonexistent_task(client, sample_data):
    user_id = sample_data["user1"].id
    payload = {
        "content": "Floating comment",
        "author_id": user_id
    }
    response = client.post("/api/v1/tasks/99999/comments", json=payload)
    assert response.status_code == 404

def test_add_comment_nonexistent_author(client, sample_data):
    task_id = sample_data["task1"].id
    payload = {
        "content": "Comment with unknown author",
        "author_id": 99999
    }
    response = client.post(f"/api/v1/tasks/{task_id}/comments", json=payload)
    assert response.status_code == 400

def test_list_comments_for_task(client, sample_data):
    task_id = sample_data["task1"].id
    response = client.get(f"/api/v1/tasks/{task_id}/comments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["content"] == "Started working on JWT verification."
