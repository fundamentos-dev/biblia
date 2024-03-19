from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlmodel import Field, Session, SQLModel, create_engine

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/jogodabiblia"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)