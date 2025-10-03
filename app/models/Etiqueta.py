from typing import Optional
from sqlmodel import Field, SQLModel


class Etiqueta(SQLModel, table=True):
    """
    Modelo para etiquetas/tags que podem ser associadas a versículos.

    Permite categorização e organização de conteúdo bíblico.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    nome: str = Field(max_length=100, index=True)
    cor: Optional[str] = Field(default="#3B82F6", max_length=7)  # Hex color
    descricao: Optional[str] = Field(default=None, max_length=500)

    def __str__(self) -> str:
        return self.nome
