from typing import Annotated

from fastapi import APIRouter
import re

from app.models.Biblia import Versao, Livro, Versiculo
from app.schemas.biblia import VersiculoSchema
from sqlmodel import Session, select
from app.database import engine


router = APIRouter(tags=["biblia"])



class ReferenciaBiblica:
    def __init__(self, livro_abrev:str, capitulo:int, versiculo:int, versao_abrev:str|None = None):
        self.livro_abrev = livro_abrev
        self.capitulo = capitulo
        self.versiculo = versiculo
        self.versao_abrev = versao_abrev
        self.texto = None

    def capturar_texto_no_banco_de_dados(self) -> str:
        with Session(engine) as session:
            try:
                stmt = select(Versiculo, Versao, Livro).where(Versiculo.versao_id == Versao.id).where(Versiculo.livro_id == Livro.id).where(Versao.abrev == self.versao_abrev).where(Livro.abrev == self.livro_abrev).where(Versiculo.capitulo == self.capitulo).where(Versiculo.numero == self.versiculo)
                result = session.exec(stmt)
                self.texto = result.first()[0].texto
            except Exception as e:
                self.texto = "Houve um erro ao recuperar esse versículo, talvez não exista."
    
    def __str__(self) -> str:
        return f'{self.livro_abrev} {self.capitulo}:{self.versiculo} {self.versao_abrev}'

    
def capturar_referencia_versiculos(referencia_biblica_string:str, lista_referencias:list|None=None) -> list[ReferenciaBiblica]:

    lista_referencias = lista_referencias or []
    # Coletando referencias de livros diferentes
    for referencia in referencia_biblica_string.split(';'):
        referencia = referencia.strip()
        if referencia == '':
            continue
        # Adicionar um espaco depois de cada virgula para textos que estão colados
        referencia = re.sub(r',\s*', ', ', referencia)
        # Captura uma referência bíblica completa
        match = re.match(r'^(\w+)\s+(\d+):(.*)$', referencia)
        versiculos_list = []
        if match:
            livro = match.group(1)
            capitulo = match.group(2)
            versiculos = match.group(3)
            for v in versiculos.split(','):
                if ':' in v:
                    lista_referencias = capturar_referencia_versiculos(
                        referencia=f'{livro}{v}', lista_referencias=lista_referencias)
                    continue
                elif '-' in v:
                    v = range(
                        int(v.split('-')[0]), int(v.split('-')[1])+1)
                    versiculos_list.extend(v)
                else:
                    versiculos_list.append(v)
            for versiculo in versiculos_list:
                lista_referencias.append(ReferenciaBiblica(livro_abrev=livro, capitulo=capitulo, versiculo=versiculo))

        else:
            raise Exception('Texto biblico no formato invalido')
    return lista_referencias


@router.get("/biblia/verse")
async def captura_versiculos_biblia_por_busca(q: Annotated[str, "Query de busca ex.: 1Pe 2:22"], versao: str = "ARA") -> list[VersiculoSchema]:
    # Captura todos os versículos indivisuais que devem ser listados para busca
    lista_referencias = capturar_referencia_versiculos(referencia_biblica_string=q)
    lista_versiculos_individuais = []
    for r in lista_referencias:
        # Captura os textos da biblia demosntrado na referência
        r.versao_abrev = versao
        r.capturar_texto_no_banco_de_dados()
        lista_versiculos_individuais.append(r)

    return lista_versiculos_individuais
