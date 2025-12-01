import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_PATH = Path(__file__).parent.parent

load_dotenv()
APP_ENV = os.getenv("APP_ENV", "production")

LOGGER_EXCEPTIONS = str(os.getenv("LOGGER_EXCEPTIONS")).lower()
LOGGER_LEVEL = os.getenv("LOGGER_LEVEL")
LOGGER_MIDDLEWARE = str(os.getenv("LOGGER_MIDDLEWARE")).lower() == "true"
LOGGER_MIDDLEWARE_SHOW_HEADERS = (
    str(os.getenv("LOGGER_MIDDLEWARE_SHOW_HEADERS")).lower() == "true"
)

DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_NAME = os.getenv("DB_NAME")
DB_PORT = os.getenv("DB_PORT")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
