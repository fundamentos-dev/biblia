from typing import Optional

from sqlmodel import Field, SQLModel


class ListaLeitura(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    titulo: str
    conteudo: str