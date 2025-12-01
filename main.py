from typing import Union

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from middlewares.LoggerMiddleware import LoggerMiddleware
from routes import email
from utils.environment import APP_ENV, LOGGER_MIDDLEWARE, SECRET_KEY

app = FastAPI()

if APP_ENV == "production" or LOGGER_MIDDLEWARE:
    app.add_middleware(LoggerMiddleware)

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.include_router(email.router)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
