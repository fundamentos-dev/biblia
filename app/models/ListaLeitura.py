from typing import Optional

from sqlmodel import Field, SQLModel


class ListaLeitura(SQLModel, table=True):
    __tablename__ = "listaleitura"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    conteudo: str