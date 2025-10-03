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
                    error_msg = "Versículo não encontrado"
                    self.texto = error_msg
                    return error_msg
            except Exception:
                error_msg = (
                    "Houve um erro ao recuperar esse versículo, talvez não exista."
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

        # MOCK DATA - Dados de demonstração
        mock_verses = {
            ("João", 3, 16): "Porque Deus amou o mundo de tal maneira que deu o seu Filho unigênito, para que todo aquele que nele crê não pereça, mas tenha a vida eterna.",
            ("João", 3, 17): "Porque Deus enviou o seu Filho ao mundo não para que condenasse o mundo, mas para que o mundo fosse salvo por ele.",
            ("João", 3, 18): "Quem nele crê não é condenado; mas quem não crê já está condenado, porquanto não crê no nome do unigênito Filho de Deus.",
            ("Gênesis", 1, 1): "No princípio, criou Deus os céus e a terra.",
            ("Gênesis", 1, 2): "E a terra era sem forma e vazia; e havia trevas sobre a face do abismo; e o Espírito de Deus se movia sobre a face das águas.",
            ("Mateus", 5, 1): "E Jesus, vendo a multidão, subiu a um monte, e, assentando-se, aproximaram-se dele os seus discípulos.",
            ("Mateus", 5, 2): "E, abrindo a boca, os ensinava, dizendo:",
            ("Mateus", 5, 3): "Bem-aventurados os pobres de espírito, porque deles é o Reino dos céus.",
            ("1Pedro", 2, 22): "O qual não cometeu pecado, nem na sua boca se achou engano.",
            ("1Pedro", 2, 23): "O qual, quando o injuriavam, não injuriava e, quando padecia, não ameaçava, mas entregava-se àquele que julga justamente.",
            ("1Pedro", 2, 24): "Levando ele mesmo em seu corpo os nossos pecados sobre o madeiro, para que, mortos para os pecados, pudéssemos viver para a justiça; e pelas suas feridas fostes sarados.",
            ("Salmos", 23, 1): "O SENHOR é o meu pastor; nada me faltará.",
            ("Salmos", 23, 2): "Deitar-me faz em verdes pastos, guia-me mansamente a águas tranquilas.",
            ("Salmos", 23, 3): "Refrigera a minha alma; guia-me pelas veredas da justiça por amor do seu nome.",
        }

        # Mapeamento de abreviações
        book_mapping = {
            "João": "João", "Jo": "João", 
            "Gênesis": "Gênesis", "Gn": "Gênesis", "Gen": "Gênesis",
            "Mateus": "Mateus", "Mt": "Mateus", "Mat": "Mateus",
            "1Pedro": "1Pedro", "1Pe": "1Pedro", "1Pd": "1Pedro",
            "Salmos": "Salmos", "Sl": "Salmos", "Sal": "Salmos",
        }

        for referencia in lista_referencias:
            # Definir versão e buscar texto no banco
            referencia.versao_abrev = versao
            
            # Tentar encontrar o livro completo
            full_book = book_mapping.get(referencia.livro_abrev, referencia.livro_abrev)
            
            # Buscar no mock data
            mock_key = (full_book, referencia.capitulo, referencia.versiculo)
            texto = mock_verses.get(mock_key, f"Versículo {referencia.livro_abrev} {referencia.capitulo}:{referencia.versiculo} - demonstração")

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
