from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.controllers import auth_controller, todo_controller
from app.services import auth_service, todo_service

app = FastAPI(title="Simple Todo API", version="2.0.0")

app.include_router(auth_controller.router)
app.include_router(todo_controller.router)


# Turn service errors into HTTP responses, so the controllers stay simple
@app.exception_handler(todo_service.TodoNotFoundError)
async def todo_not_found_handler(request: Request, exc: todo_service.TodoNotFoundError):
    return JSONResponse(status_code=404, content={"detail": "Todo not found"})


@app.exception_handler(auth_service.UsernameTakenError)
async def username_taken_handler(request: Request, exc: auth_service.UsernameTakenError):
    return JSONResponse(status_code=409, content={"detail": "Username already taken"})


@app.exception_handler(auth_service.InvalidCredentialsError)
async def invalid_credentials_handler(request: Request, exc: auth_service.InvalidCredentialsError):
    return JSONResponse(
        status_code=401,
        content={"detail": "Incorrect username or password"},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/")
def root():
    return {"message": "Todo API is running. Visit /docs for the API docs."}
