def test_dashboard_stats(client, sample_data):
    response = client.get("/api/v1/dashboard/stats")
    assert response.status_code == 200
    data = response.json()

    assert data["total_projects"] == 1
    assert data["total_tasks"] == 3
    # In sample_data: task3 is "done" (completed), task1 is "in_progress", task2 is "todo"
    assert data["completed_tasks"] == 1
    assert data["pending_tasks"] == 2
    # task2 is past due and "todo" -> overdue!
    # task3 is past due but "done" -> NOT overdue!
    assert data["overdue_tasks"] == 1

    # Check status breakdown
    assert data["tasks_by_status"]["todo"] == 1
    assert data["tasks_by_status"]["in_progress"] == 1
    assert data["tasks_by_status"]["done"] == 1

    # Check priority breakdown
    assert data["tasks_by_priority"]["high"] == 1
    assert data["tasks_by_priority"]["low"] == 1
    assert data["tasks_by_priority"]["medium"] == 1

    # Check recent tasks and projects list
    assert len(data["recent_tasks"]) <= 5
    assert len(data["recent_projects"]) <= 5
