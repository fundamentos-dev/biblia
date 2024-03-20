from sqlmodel import create_engine
import os

engine = create_engine(
    os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@db:5432/biblia")
)