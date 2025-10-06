from pydantic import BaseModel, Field
from typing import Optional


class VersiculoSchema(BaseModel):
    """Schema para retorno de versículos bíblicos nas APIs."""

    versao_abrev: str = Field(..., description="Abreviação da versão da Bíblia")
    livro_abrev: str = Field(..., description="Abreviação do livro bíblico")
    capitulo: int = Field(..., gt=0, description="Número do capítulo")
    versiculo: int = Field(..., gt=0, description="Número do versículo")
    texto: str = Field(..., description="Texto do versículo")

    class Config:
        json_schema_extra = {
            "example": {
                "versao_abrev": "ARA",
                "livro_abrev": "Jo",
                "capitulo": 3,
                "versiculo": 16,
                "texto": "Porque Deus amou ao mundo de tal maneira...",
            }
        }


class LivroSchema(BaseModel):
    """Schema para informações de livros bíblicos."""

    id: int
    nome: str = Field(..., description="Nome completo do livro")
    abrev: str = Field(..., description="Abreviação do livro")
    posicao: int = Field(..., description="Posição do livro na Bíblia")
    testamento_id: int = Field(..., description="ID do testamento")


class BuscaVersiculoRequest(BaseModel):
    """Schema para requisições de busca de versículos."""

    query: str = Field(..., description="Texto de busca (ex: 'João 3:16')")
    versao: Optional[str] = Field("ARA", description="Versão da Bíblia")

    class Config:
        json_schema_extra = {
            "example": {"query": "João 3:16-17; 1Pe 2:9", "versao": "ARA"}
        }


class ListaLeituraSchema(BaseModel):
    """Schema para retorno de listas de leitura."""

    id: int
    titulo: str = Field(..., description="Título da lista de leitura")
    conteudo: str = Field(..., description="Conteúdo da lista de leitura")

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "titulo": "Vida em Cristo",
                "conteudo": "João 3:16; Romanos 8:1; 1 João 5:11-13"
            }
        }


class ListaLeituraResponse(BaseModel):
    """Schema para resposta paginada de listas de leitura."""

    items: list[ListaLeituraSchema] = Field(..., description="Lista de listas de leitura")
    total: int = Field(..., description="Total de itens encontrados")
    page: int = Field(..., description="Página atual")
    size: int = Field(..., description="Tamanho da página")
    total_pages: int = Field(..., description="Total de páginas")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": 1,
                        "titulo": "Vida em Cristo", 
                        "conteudo": "João 3:16; Romanos 8:1"
                    }
                ],
                "total": 15,
                "page": 1,
                "size": 10,
                "total_pages": 2
            }
        }
