from typing import Optional

from sqlmodel import Field, SQLModel


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
