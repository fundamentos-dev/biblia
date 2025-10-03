import re
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, select

from app.database import engine
from app.models.Biblia import Livro, LivroCapituloNumeroVersiculos, Versao, Versiculo
from app.schemas.biblia import VersiculoSchema


router = APIRouter(tags=["biblia"])


class ReferenciaBiblica:
    """
    Representa uma referência bíblica com livro, capítulo, versículo e versão.

    Encapsula as operações de busca e formatação de versículos bíblicos.
    """

    def __init__(
        self,
        livro_abrev: str,
        capitulo: int,
        versiculo: int,
        versao_abrev: Optional[str] = None,
    ):
        self.livro_abrev = livro_abrev
        self.capitulo = capitulo
        self.versiculo = versiculo
        self.versao_abrev = versao_abrev
        self.texto: Optional[str] = None

    def capturar_texto_no_banco_de_dados(self) -> str:
        """
        Busca o texto do versículo no banco de dados.

        Returns:
            str: Texto do versículo ou mensagem de erro

        Raises:
            ValueError: Se a referência bíblica for inválida
        """
        if not self.versao_abrev:
            raise ValueError("Versão da bíblia deve ser especificada")

        with Session(engine) as session:
            try:
                # Debug: verificar se versão e livro existem
                versao_query = select(Versao).where(Versao.abrev == self.versao_abrev)
                versao_result = session.exec(versao_query).first()
                
                livro_query = select(Livro).where(Livro.abrev == self.livro_abrev)
                livro_result = session.exec(livro_query).first()
                
                if not versao_result:
                    return f"Versão '{self.versao_abrev}' não encontrada no banco"
                
                if not livro_result:
                    return f"Livro '{self.livro_abrev}' não encontrado no banco"
                
                # Busca principal
                stmt = (
                    select(Versiculo, Versao, Livro)
                    .where(Versiculo.versao_id == Versao.id)
                    .where(Versiculo.livro_id == Livro.id)
                    .where(Versao.abrev == self.versao_abrev)
                    .where(Livro.abrev == self.livro_abrev)
                    .where(Versiculo.capitulo == self.capitulo)
                    .where(Versiculo.numero == self.versiculo)
                )
                result = session.exec(stmt).first()
                if result:
                    versiculo_data, _, _ = (
                        result  # Desempacota o tuple (Versiculo, Versao, Livro)
                    )
                    texto = str(versiculo_data.texto or "Texto não disponível")
                    self.texto = texto
                    return texto
                else:
                    return f"Versículo {self.livro_abrev} {self.capitulo}:{self.versiculo} não encontrado na versão {self.versao_abrev}"
            except Exception as e:
                error_msg = (
                    f"Erro ao recuperar versículo {self.livro_abrev} {self.capitulo}:{self.versiculo}: {str(e)}"
                )
                self.texto = error_msg
                return error_msg

    def __str__(self) -> str:
        return (
            f"{self.livro_abrev} {self.capitulo}:{self.versiculo} {self.versao_abrev}"
        )


def capturar_referencia_versiculos(
    referencia_biblica_string: str,
    lista_referencias: Optional[list[ReferenciaBiblica]] = None,
) -> list[ReferenciaBiblica]:
    """
    Parser de referências bíblicas que suporta múltiplos formatos.

    Formatos suportados:
    - "João 3:16" - versículo único
    - "João 3:16-18" - faixa de versículos
    - "João 3:16,17,18" - múltiplos versículos
    - "João 3:16; Mateus 5:1" - múltiplos livros

    Args:
        referencia_biblica_string: String com referências no formato padrão
        lista_referencias: Lista existente para acumular resultados

    Returns:
        list[ReferenciaBiblica]: Lista de referências parseadas

    Raises:
        ValueError: Se o formato da referência for inválido
    """
    if lista_referencias is None:
        lista_referencias = []

    # Processamento de múltiplos livros separados por ponto-e-vírgula
    for referencia in referencia_biblica_string.split(";"):
        referencia = referencia.strip()
        if not referencia:
            continue

        # Normalizar espaçamento após vírgulas
        referencia = re.sub(r",\s*", ", ", referencia)

        # Pattern: "Livro Capitulo:Versiculos"
        match = re.match(r"^(\w+)\s+(\d+):(.*)$", referencia)
        if not match:
            raise ValueError(f"Formato de referência bíblica inválido: {referencia}")

        livro = match.group(1)
        capitulo_str = match.group(2)
        versiculos_str = match.group(3)

        try:
            capitulo = int(capitulo_str)
        except ValueError:
            raise ValueError(f"Capítulo inválido: {capitulo_str}")

        versiculos_list: list[int] = []

        # Processar cada parte dos versículos (separados por vírgula)
        for v in versiculos_str.split(","):
            v = v.strip()

            # Referência a outro capítulo (ex: "João 3:16, 4:2")
            if ":" in v:
                nova_ref = f"{livro} {v}"
                lista_referencias.extend(capturar_referencia_versiculos(nova_ref, []))
                continue

            # Faixa de versículos (ex: "16-18")
            elif "-" in v:
                try:
                    inicio, fim = v.split("-", 1)
                    versiculos_list.extend(range(int(inicio), int(fim) + 1))
                except ValueError:
                    raise ValueError(f"Faixa de versículos inválida: {v}")
            # Versículo único
            else:
                try:
                    versiculos_list.append(int(v))
                except ValueError:
                    raise ValueError(f"Número de versículo inválido: {v}")

        # Criar objetos ReferenciaBiblica para cada versículo
        for versiculo in versiculos_list:
            lista_referencias.append(
                ReferenciaBiblica(
                    livro_abrev=livro, capitulo=capitulo, versiculo=versiculo
                )
            )

    return lista_referencias


@router.get("/biblia/verse")
async def captura_versiculos_biblia_por_busca(
    q: Annotated[str, "Query de busca ex.: 1Pe 2:22"], versao: str = "ARA"
) -> list[VersiculoSchema]:
    """
    Busca versículos bíblicos baseado em referências textuais.

    Args:
        q: String com referências bíblicas (ex: "João 3:16", "1Pe 2:22-24")
        versao: Versão da bíblia (padrão: ARA)

    Returns:
        list[VersiculoSchema]: Lista de versículos encontrados

    Raises:
        HTTPException: Se o formato da query for inválido
    """
    try:
        # Captura todas as referências individuais parseadas da query
        lista_referencias = capturar_referencia_versiculos(referencia_biblica_string=q)
        lista_versiculos_individuais = []

        for referencia in lista_referencias:
            # Definir versão e buscar texto no banco de dados
            referencia.versao_abrev = versao
            texto = referencia.capturar_texto_no_banco_de_dados()

            # Converter para schema de retorno
            versiculo_schema = VersiculoSchema(
                versao_abrev=versao,
                livro_abrev=referencia.livro_abrev,
                capitulo=referencia.capitulo,
                versiculo=referencia.versiculo,
                texto=texto,
            )
            lista_versiculos_individuais.append(versiculo_schema)

        return lista_versiculos_individuais

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


@router.get("/biblia/books")
async def get_all_books() -> list[Livro]:
    """
    Retorna todos os livros da bíblia cadastrados.

    Returns:
        list[Livro]: Lista de todos os livros bíblicos
    """
    try:
        with Session(engine) as session:
            stmt = select(Livro).order_by(Livro.posicao)
            result = session.exec(stmt).all()
        return list(result)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao buscar livros")


@router.get("/biblia/book/{book_id}/chapters")
async def get_number_of_chapters(book_id: int) -> int:
    """
    Retorna o número de capítulos de um livro específico.

    Args:
        book_id: ID do livro bíblico

    Returns:
        int: Número total de capítulos do livro
    """
    try:
        with Session(engine) as session:
            stmt = select(LivroCapituloNumeroVersiculos).where(
                LivroCapituloNumeroVersiculos.livro_id == book_id
            )
            result = session.exec(stmt).all()
        return len(result)
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao buscar capítulos")


@router.get("/biblia/book/{book_id}/chapter/{chapter_number}/verses")
async def get_number_of_verses(book_id: int, chapter_number: int) -> int:
    """
    Retorna o número de versículos de um capítulo específico.

    Args:
        book_id: ID do livro bíblico
        chapter_number: Número do capítulo

    Returns:
        int: Número total de versículos do capítulo
    """
    try:
        with Session(engine) as session:
            stmt = select(LivroCapituloNumeroVersiculos).where(
                LivroCapituloNumeroVersiculos.livro_id == book_id,
                LivroCapituloNumeroVersiculos.capitulo == chapter_number,
            )
            result = session.exec(stmt).first()
        return result.total_versiculos if result else 0
    except Exception:
        raise HTTPException(status_code=500, detail="Erro ao buscar versículos")
