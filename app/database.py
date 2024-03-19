from sqlmodel import Field, Session, SQLModel, create_engine, select

DATABASE_URL = "postgresql://postgres:postgres@db:5432/jogodabiblia"
engine = create_engine(DATABASE_URL, echo=True)