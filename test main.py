import pytest
from fastapi.testclient import TestClient

import main
from app.services import auth_service, todo_service

client = TestClient(main.app)        # sends the Authorization header once logged in
anon_client = TestClient(main.app)   # never sends a token

PASSWORD = "password123"


def register_and_login(username: str) -> dict:
    """Create a user, log in, and return the Authorization header."""
    client.post("/auth/register", json={"username": username, "password": PASSWORD})
    response = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def reset_all():
    todo_service.todos.clear()
    todo_service.next_id = 1
    auth_service.users.clear()
    auth_service.next_user_id = 1
    client.headers.clear()


@pytest.fixture(autouse=True)
def fresh_state():
    """Empty stores, then log in as 'tester' for every test."""
    reset_all()
    client.headers.update(register_and_login("tester"))
    yield
    reset_all()


def create(title="Task", **extra):
    response = client.post("/todos", json={"title": title, **extra})
    assert response.status_code == 201
    return response.json()


# ---------- basic ----------

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_list_empty():
    assert client.get("/todos").json() == []


# ---------- auth ----------

def test_register_returns_user_without_password():
    response = client.post("/auth/register", json={"username": "newbie", "password": PASSWORD})
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "newbie"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_username():
    response = client.post("/auth/register", json={"username": "tester", "password": PASSWORD})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "password": PASSWORD},         # username too short
        {"username": "bad name!", "password": PASSWORD},  # invalid characters
        {"username": "validuser", "password": "short"},   # password too short
        {"username": "validuser", "password": "x" * 73},  # password too long
    ],
)
def test_register_invalid(payload):
    assert client.post("/auth/register", json=payload).status_code == 422


def test_login_success_returns_token():
    response = client.post("/auth/login", data={"username": "tester", "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password():
    response = client.post("/auth/login", data={"username": "tester", "password": "wrong-pass"})
    assert response.status_code == 401


def test_login_unknown_user():
    response = client.post("/auth/login", data={"username": "nobody", "password": PASSWORD})
    assert response.status_code == 401


def test_me_returns_current_user():
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "tester"


def test_todos_require_token():
    assert anon_client.get("/todos").status_code == 401
    assert anon_client.post("/todos", json={"title": "x"}).status_code == 401


def test_invalid_token_rejected():
    response = anon_client.get("/todos", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_users_cannot_see_each_others_todos():
    create("tester's task")
    client.headers.update(register_and_login("other"))
    assert client.get("/todos").json() == []
    assert client.get("/todos/1").status_code == 404
    assert client.patch("/todos/1/complete").status_code == 404
    assert client.delete("/todos/1").status_code == 404


def test_todo_lists_are_separate():
    create("tester task")
    client.headers.update(register_and_login("other"))
    create("other task")
    titles = [t["title"] for t in client.get("/todos").json()]
    assert titles == ["other task"]


# ---------- create ----------

def test_create_with_defaults():
    todo = create("Buy milk")
    assert todo == {
        "id": 1,
        "title": "Buy milk",
        "description": None,
        "completed": False,
        "priority": "medium",
    }


def test_create_with_all_fields():
    todo = create("Report", description="Q4 report", priority="high", completed=True)
    assert todo["priority"] == "high"
    assert todo["completed"] is True
    assert todo["description"] == "Q4 report"


def test_ids_increase():
    assert create("a")["id"] == 1
    assert create("b")["id"] == 2


@pytest.mark.parametrize(
    "payload",
    [
        {},                                     # title missing
        {"title": ""},                          # title empty
        {"title": "x" * 201},                   # title too long
        {"title": "x", "priority": "urgent"},   # invalid priority
    ],
)
def test_create_invalid(payload):
    assert client.post("/todos", json=payload).status_code == 422


# ---------- read ----------

def test_get_one():
    create("Read me")
    response = client.get("/todos/1")
    assert response.status_code == 200
    assert response.json()["title"] == "Read me"


def test_get_missing_returns_404():
    response = client.get("/todos/99")
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"


# ---------- priority ----------

def test_list_sorted_by_priority():
    create("low", priority="low")
    create("medium")
    create("high", priority="high")
    titles = [t["title"] for t in client.get("/todos").json()]
    assert titles == ["high", "medium", "low"]


def test_same_priority_keeps_creation_order():
    create("first", priority="high")
    create("second", priority="high")
    titles = [t["title"] for t in client.get("/todos").json()]
    assert titles == ["first", "second"]


def test_filter_by_priority():
    create("a", priority="high")
    create("b", priority="low")
    result = client.get("/todos", params={"priority": "high"}).json()
    assert [t["title"] for t in result] == ["a"]


def test_filter_invalid_priority():
    assert client.get("/todos", params={"priority": "urgent"}).status_code == 422


def test_set_priority():
    create("task")
    response = client.patch("/todos/1/priority", params={"priority": "high"})
    assert response.status_code == 200
    assert response.json()["priority"] == "high"


def test_set_priority_missing_todo():
    response = client.patch("/todos/99/priority", params={"priority": "high"})
    assert response.status_code == 404


def test_set_priority_invalid_value():
    create("task")
    response = client.patch("/todos/1/priority", params={"priority": "urgent"})
    assert response.status_code == 422


# ---------- completed / pending ----------

def test_mark_completed():
    create("task")
    response = client.patch("/todos/1/complete")
    assert response.status_code == 200
    assert response.json()["completed"] is True
    assert client.get("/todos/1").json()["completed"] is True


def test_mark_completed_missing_todo():
    assert client.patch("/todos/99/complete").status_code == 404


def test_completed_endpoint():
    create("done", completed=True)
    create("not done")
    result = client.get("/todos/completed").json()
    assert [t["title"] for t in result] == ["done"]


def test_pending_endpoint_sorted_by_priority():
    create("low", priority="low")
    create("high", priority="high")
    create("finished", priority="high", completed=True)
    result = client.get("/todos/pending").json()
    assert [t["title"] for t in result] == ["high", "low"]


def test_filter_completed_and_priority_together():
    create("high open", priority="high")
    create("high done", priority="high", completed=True)
    create("low open", priority="low")
    result = client.get("/todos", params={"completed": False, "priority": "high"}).json()
    assert [t["title"] for t in result] == ["high open"]


def test_completed_route_not_treated_as_id():
    assert client.get("/todos/completed").status_code == 200
    assert client.get("/todos/pending").status_code == 200


# ---------- update ----------

def test_partial_update_keeps_other_fields():
    create("old", description="keep me", priority="low")
    response = client.patch("/todos/1", json={"title": "new"})
    todo = response.json()
    assert todo["title"] == "new"
    assert todo["description"] == "keep me"
    assert todo["priority"] == "low"


def test_null_title_is_not_saved():
    create("keep this title")
    client.patch("/todos/1", json={"title": None})
    assert client.get("/todos/1").json()["title"] == "keep this title"


def test_update_missing_todo():
    assert client.patch("/todos/99", json={"title": "x"}).status_code == 404


def test_update_invalid_priority():
    create("task")
    assert client.patch("/todos/1", json={"priority": "urgent"}).status_code == 422


# ---------- delete ----------

def test_delete():
    create("task")
    assert client.delete("/todos/1").status_code == 204
    assert client.get("/todos/1").status_code == 404


def test_delete_missing_todo():
    assert client.delete("/todos/99").status_code == 404
