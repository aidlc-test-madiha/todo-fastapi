# Simple Todo API (FastAPI)

A minimal CRUD Todo API built with FastAPI. Data is stored in memory.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs for the interactive Swagger UI.

## Endpoints

| Method | Path              | Description                          |
|--------|-------------------|--------------------------------------|
| GET    | `/todos`          | List todos (optional `?completed=`)  |
| GET    | `/todos/{id}`     | Get one todo                         |
| POST   | `/todos`          | Create a todo                        |
| PATCH  | `/todos/{id}`     | Update a todo                        |
| DELETE | `/todos/{id}`     | Delete a todo                        |
