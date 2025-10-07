import re
import unicodedata
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select

from app.database import engine
from app.models.Biblia import Livro, LivroCapituloNumeroVersiculos, Versao, Versiculo
from app.schemas.biblia import VersiculoSchema, ListaLeituraResponse, ListaLeituraSchema
from app.semantic_search import semantic_search_service


router = APIRouter(tags=["biblia"])


def normalizar_texto(texto: str) -> str:
    """
    Remove acentos e converte texto para minúsculas para comparação.
    
    Args:
        texto: Texto para normalizar
        
    Returns:
        Texto normalizado sem acentos e em minúsculas
    """
    texto_nfd = unicodedata.normalize('NFD', texto)
    texto_sem_acentos = texto_nfd.encode('ascii', 'ignore').decode('ascii')
    return texto_sem_acentos.lower().strip()


def criar_mapeamento_livros() -> dict[str, str]:
    """
    Cria mapeamento de nomes normalizados para abreviações dos livros.

    Inclui tanto nomes completos quanto abreviações para máxima flexibilidade.

    Returns:
        Dicionário com nome_normalizado -> abreviação
    """
    mapeamento = {}

    try:
        with Session(engine) as session:
            stmt = select(Livro)
            livros = session.exec(stmt).all()

            for livro in livros:
                # Mapear abreviação exata -> abreviação
                mapeamento[livro.abrev] = livro.abrev

                # Mapear nome completo normalizado -> abreviação
                nome_normalizado = normalizar_texto(livro.nome)
                mapeamento[nome_normalizado] = livro.abrev

                # Mapear abreviação normalizada -> abreviação (para manter compatibilidade)
                abrev_normalizada = normalizar_texto(livro.abrev)
                if abrev_normalizada not in mapeamento:
                    mapeamento[abrev_normalizada] = livro.abrev

    except Exception as e:
        # Se houver erro no banco, usar fallback com dados conhecidos
        livros_fallback = [
            ("Genesis", "Gn"), ("Exodo", "Ex"), ("Levitico", "Lv"), ("Numeros", "Nm"),
            ("Deuteronomio", "Dt"), ("Josue", "Js"), ("Juizes", "Jz"), ("Rute", "Rt"),
            ("I Samuel", "1Sm"), ("II Samuel", "2Sm"), ("I Reis", "1Rs"), ("II Reis", "2Rs"),
            ("I Cronicas", "1Cr"), ("II Cronicas", "2Cr"), ("Esdras", "Ed"), ("Neemias", "Ne"),
            ("Ester", "Et"), ("Jó", "Jó"), ("Salmos", "Sl"), ("Proverbios", "Pv"),
            ("Eclesiastes", "Ec"), ("Cantico dos Canticos", "Ct"), ("Isaias", "Is"),
            ("Jeremias", "Jr"), ("Lamentacoes Jeremias", "Lm"), ("Ezequiel", "Ez"),
            ("Daniel", "Dn"), ("Oseias", "Os"), ("Joel", "Jl"), ("Amos", "Am"),
            ("Obadias", "Ob"), ("Jonas", "Jn"), ("Miqueias", "Mq"), ("Naum", "Na"),
            ("Habacuque", "Hc"), ("Sofonias", "Sf"), ("Ageu", "Ag"), ("Zacarias", "Zc"),
            ("Malaquias", "Ml"), ("Mateus", "Mt"), ("Marcos", "Mc"), ("Lucas", "Lc"),
            ("Joao", "Jo"), ("Atos", "At"), ("Romanos", "Rm"), ("I Corintios", "1Co"),
            ("II Corintios", "2Co"), ("Galatas", "Gl"), ("Efesios", "Ef"), ("Filipenses", "Fp"),
            ("Colossenses", "Cl"), ("I Tessalonicenses", "1Ts"), ("II Tessalonicenses", "2Ts"),
            ("I Timoteo", "1Tm"), ("II Timoteo", "2Tm"), ("Tito", "Tt"), ("Filemom", "Fm"),
            ("Hebreus", "Hb"), ("Tiago", "Tg"), ("I Pedro", "1Pe"), ("II Pedro", "2Pe"),
            ("I Joao", "1Jo"), ("II Joao", "2Jo"), ("III Joao", "3Jo"), ("Judas", "Jd"),
            ("Apocalipse", "Ap")
        ]

        # Reverter para priorizar IDs maiores (João sobre Jó)
        livros_fallback.reverse()

        for nome, abrev in livros_fallback:
            # Mapear abreviação exata -> abreviação
            mapeamento[abrev] = abrev

            nome_normalizado = normalizar_texto(nome)
            mapeamento[nome_normalizado] = abrev
            abrev_normalizada = normalizar_texto(abrev)
            if abrev_normalizada not in mapeamento:
                mapeamento[abrev_normalizada] = abrev

    return mapeamento


# Cache do mapeamento para evitar consultas desnecessárias ao banco
_mapeamento_livros_cache: Optional[dict[str, str]] = None


def obter_abreviacao_livro(nome_livro: str) -> str:
    """
    Obtém a abreviação do livro a partir do nome (com ou sem acentos).

    Args:
        nome_livro: Nome do livro (pode ter acentos, maiúsculas/minúsculas)

    Returns:
        Abreviação do livro

    Raises:
        ValueError: Se o livro não for encontrado
    """
    global _mapeamento_livros_cache

    if _mapeamento_livros_cache is None:
        _mapeamento_livros_cache = criar_mapeamento_livros()

    # Verificar correspondência exata primeiro
    if nome_livro in _mapeamento_livros_cache:
        return _mapeamento_livros_cache[nome_livro]

    # Verificar correspondência normalizada
    nome_normalizado = normalizar_texto(nome_livro)

    if nome_normalizado in _mapeamento_livros_cache:
        return _mapeamento_livros_cache[nome_normalizado]

    raise ValueError(f"Livro não encontrado: {nome_livro}")


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
                versao_query = select(Versao).where(Versao.abrev == self.versao_abrev).where(Versao.active == True)
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
                    .where(Versao.active == True)
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
    - "João 3:16" ou "Joao 3:16" - versículo único (com ou sem acentos)
    - "I Coríntios 13:4" ou "1 Corintios 13:4" - nomes completos
    - "Jo 3:16" ou "1Co 13:4" - abreviações
    - "João 3:16-18" - faixa de versículos
    - "João 3:16,17,18" - múltiplos versículos
    - "João 3:16; Mateus 5:1" - múltiplos livros

    O parser normaliza automaticamente acentos, permitindo entrada flexível:
    - "Gênesis" = "Genesis"
    - "Êxodo" = "Exodo"
    - "Coríntios" = "Corintios"

    Args:
        referencia_biblica_string: String com referências no formato padrão
        lista_referencias: Lista existente para acumular resultados

    Returns:
        list[ReferenciaBiblica]: Lista de referências parseadas

    Raises:
        ValueError: Se o formato da referência for inválido ou livro não encontrado
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

        # Pattern: "Livro Capitulo:Versiculos" (aceita múltiplas palavras e acentos)
        match = re.match(r"^([A-Za-z\s\u00C0-\u017F0-9]+)\s+(\d+):(.*)$", referencia)
        if not match:
            raise ValueError(f"Formato de referência bíblica inválido: {referencia}")

        livro_nome = match.group(1).strip()
        
        # Resolver nome do livro para abreviação usando normalização
        try:
            livro = obter_abreviacao_livro(livro_nome)
        except ValueError as e:
            raise ValueError(f"Livro não encontrado: {livro_nome}") from e
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
    q: Annotated[str, "Query de busca ex.: 1Pe 2:22 ou texto livre para busca semântica"],
    versao: str = "ARA",
    ss: bool = Query(False, description="Ativar busca semântica")
) -> list[VersiculoSchema]:
    """
    Busca versículos bíblicos baseado em referências textuais ou busca semântica.

    Args:
        q: String com referências bíblicas (ex: "João 3:16") ou texto livre para busca semântica
        versao: Versão da bíblia (padrão: ARA)
        ss: Ativar busca semântica (padrão: False)

    Returns:
        list[VersiculoSchema]: Lista de versículos encontrados

    Raises:
        HTTPException: Se o formato da query for inválido ou erro na busca
    """
    # Se ss=true, fazer busca semântica
    if ss:
        try:
            # Realizar busca semântica
            results = await semantic_search_service.search(
                query=q,
                limit=5,
                versao_abrev=versao
            )
            
            # Ordenar por score (maior primeiro) e converter para VersiculoSchema
            results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
            lista_versiculos = []
            for result in results:
                versiculo_schema = VersiculoSchema(
                    versao_abrev=result.get("versao_abrev", versao),
                    livro_abrev=result.get("livro_abrev", ""),
                    capitulo=result.get("capitulo", 0),
                    versiculo=result.get("numero", 0),
                    texto=result.get("text", ""),
                )
                lista_versiculos.append(versiculo_schema)
            
            return lista_versiculos
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro na busca semântica: {str(e)}"
            )
    
    # Busca tradicional por referência
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
            stmt = select(Livro)
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
