from enum import Enum

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Simple Todo API", version="1.1.0")


class Priority(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


# Used to sort todos: high first, low last
PRIORITY_ORDER = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False
    priority: Priority = Priority.medium


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None
    priority: Priority | None = None


class Todo(TodoCreate):
    id: int


# In-memory storage (resets when the server restarts)
todos: dict[int, Todo] = {}
next_id = 1


def get_or_404(todo_id: int) -> Todo:
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]


def sort_by_priority(items: list[Todo]) -> list[Todo]:
    return sorted(items, key=lambda t: (PRIORITY_ORDER[t.priority], t.id))


@app.get("/")
def root():
    return {"message": "Todo API is running. Visit /docs for the API docs."}


@app.get("/todos", response_model=list[Todo])
def list_todos(completed: bool | None = None, priority: Priority | None = None):
    """List todos, sorted high -> medium -> low. Optional filters: completed, priority."""
    items = list(todos.values())
    if completed is not None:
        items = [t for t in items if t.completed == completed]
    if priority is not None:
        items = [t for t in items if t.priority == priority]
    return sort_by_priority(items)


@app.get("/todos/completed", response_model=list[Todo])
def list_completed_todos():
    """Only the todos where completed is true."""
    return sort_by_priority([t for t in todos.values() if t.completed])


@app.get("/todos/pending", response_model=list[Todo])
def list_pending_todos():
    """Only the todos still to do, highest priority first."""
    return sort_by_priority([t for t in todos.values() if not t.completed])


@app.get("/todos/{todo_id}", response_model=Todo)
def get_todo(todo_id: int):
    return get_or_404(todo_id)


@app.post("/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate):
    global next_id
    todo = Todo(id=next_id, **payload.model_dump())
    todos[next_id] = todo
    next_id += 1
    return todo


@app.patch("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, payload: TodoUpdate):
    todo = get_or_404(todo_id)
    updated = todo.model_copy(update=payload.model_dump(exclude_unset=True))
    todos[todo_id] = updated
    return updated


@app.patch("/todos/{todo_id}/complete", response_model=Todo)
def mark_completed(todo_id: int):
    """Set completed = true."""
    todo = get_or_404(todo_id)
    todos[todo_id] = todo.model_copy(update={"completed": True})
    return todos[todo_id]


@app.patch("/todos/{todo_id}/priority", response_model=Todo)
def set_priority(todo_id: int, priority: Priority):
    """Change priority, e.g. PATCH /todos/1/priority?priority=high"""
    todo = get_or_404(todo_id)
    todos[todo_id] = todo.model_copy(update={"priority": priority})
    return todos[todo_id]


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int):
    get_or_404(todo_id)
    del todos[todo_id]
