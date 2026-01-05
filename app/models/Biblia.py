from typing import Optional, List, Any

from sqlmodel import Field, SQLModel
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TSVECTOR


class Testamento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str

    def __str__(self):
        return self.nome


class Livro(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    posicao: int
    nome: str
    abrev: str
    testamento_id: int = Field(foreign_key="testamento.id")


class Versiculo(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    capitulo: int
    numero: int
    texto: str
    livro_id: int = Field(foreign_key="livro.id")
    versao_id: int = Field(foreign_key="versao.id")
    
    embedding_1536_serafim_900m: Optional[List[float]] = Field(default=None, sa_column=Column(Vector(1536)))
    tsv: Optional[Any] = Field(default=None, sa_column=Column(TSVECTOR))

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        return f"v{self.numero}:{self.numero}"


class Versao(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str
    abrev: str
    active: bool = Field(default=True)

    def __str__(self):
        return self.nome


class LivroCapituloNumeroVersiculos(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    capitulo: int
    total_versiculos: int
    livro_id: int = Field(foreign_key="livro.id")
