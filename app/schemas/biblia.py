from pydantic import BaseModel


class VersiculoSchema(BaseModel):
    versao_abrev: str
    livro_abrev: str
    capitulo: int
    versiculo: int
    texto: str