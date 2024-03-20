from sqlmodel import create_engine
import os

DATABASE_URL = f'postgres://{os.environ.get("DB_USER", "postgres")}:{os.environ.get("DB_PASS", "postgres")}@{os.environ.get("DB_HOST", "db")}/{os.environ.get("DB_NAME", "biblia")}'

engine = create_engine(DATABASE_URL)

print(f'Conectado a {DATABASE_URL}')