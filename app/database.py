from sqlmodel import create_engine
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/biblia")

engine = create_engine(DATABASE_URL)

print(f'Conectado a {DATABASE_URL}')