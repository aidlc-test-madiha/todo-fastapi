from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Simple Todo API", version="1.0.0")


class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False


class TodoUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None


class Todo(TodoCreate):
    id: int


# In-memory storage (resets when the server restarts)
todos: dict[int, Todo] = {}
next_id = 1


@app.get("/")
def root():
    return {"message": "Todo API is running. Visit /docs for the API docs."}


@app.get("/todos", response_model=list[Todo])
def list_todos(completed: bool | None = None):
    items = list(todos.values())
    if completed is not None:
        items = [t for t in items if t.completed == completed]
    return items


@app.get("/todos/{todo_id}", response_model=Todo)
def get_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]


@app.post("/todos", response_model=Todo, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate):
    global next_id
    todo = Todo(id=next_id, **payload.model_dump())
    todos[next_id] = todo
    next_id += 1
    return todo


@app.patch("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: int, payload: TodoUpdate):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    updated = todos[todo_id].model_copy(update=payload.model_dump(exclude_unset=True))
    todos[todo_id] = updated
    return updated


@app.delete("/todos/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int):
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    del todos[todo_id]
