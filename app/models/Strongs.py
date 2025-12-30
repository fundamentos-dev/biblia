from typing import Optional
from sqlmodel import Field, SQLModel


class StrongsEntry(SQLModel, table=True):
    __tablename__ = "strongs_entry"

    strong: str = Field(primary_key=True, description="Código Strong (ex: H1234, G1234)")
    lemma: Optional[str] = Field(default=None, description="Palavra original (lema)")
    transliteration: Optional[str] = Field(default=None, description="Transliteração")
    pronunciation: Optional[str] = Field(default=None, description="Pronúncia")
    derivation: Optional[str] = Field(default=None, description="Origem/Derivação")
    def_short: Optional[str] = Field(default=None, description="Definição curta")
    def_long: Optional[str] = Field(default=None, description="Definição completa")


class OriginalToken(SQLModel, table=True):
    __tablename__ = "original_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    livro_id: int = Field(foreign_key="livro.id", index=True, description="ID do livro (1-66)")
    capitulo: int = Field(index=True)
    versiculo: int = Field(index=True)
    sequence_order: int = Field(description="Posição da palavra no versículo")
    surface: str = Field(description="Palavra no texto original")
    strong: Optional[str] = Field(default=None, foreign_key="strongs_entry.strong", index=True, description="Código Strong associado")
    morph: Optional[str] = Field(default=None, description="Morfologia")
