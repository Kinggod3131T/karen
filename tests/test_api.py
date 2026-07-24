from fastapi.testclient import TestClient

from services.core.app.main import app


client = TestClient(app)


def test_root_is_online() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_karen_1_workflow_routes_exist() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200

    available_paths = set(response.json()["paths"])

    required_paths = {
        "/workflow/tasks",
        "/workflow/tasks/{task_id}",
        "/workflow/tasks/{task_id}/approve",
        "/workflow/tasks/{task_id}/reject",
    }

    missing_paths = required_paths - available_paths

    assert not missing_paths, (
        f"Missing Karen workflow routes: {sorted(missing_paths)}"
    )
