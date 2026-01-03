import logging
import httpx
import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from sqlmodel import Session, text

from app.database import engine

# Carregar variáveis de ambiente com override=True
load_dotenv(override=True)

logger = logging.getLogger("api.semantic_search")

class SemanticSearch:
    def __init__(
        self,
        ollama_host: str = "ollama",
        ollama_port: int = 11434,
        embedding_model: str = "qwen3-embedding-4b-gguf-q8_0",
        embedding_dim: Optional[int] = None,
        embedding_provider: str = "ollama",
        llama_cpp_embed_url: Optional[str] = None,
        hnsw_ef_search: int = 64,
    ):
        self.ollama_host = os.getenv("OLLAMA_HOST", ollama_host)
        self.ollama_port = int(os.getenv("OLLAMA_PORT", ollama_port))
        self.embedding_model = os.getenv("EMBEDDING_MODEL", embedding_model)
        self.embedding_provider = os.getenv(
            "EMBEDDING_PROVIDER",
            embedding_provider
        ).lower()
        self.llama_cpp_embed_url = os.getenv(
            "LLAMA_CPP_EMBED_URL",
            llama_cpp_embed_url or ""
        )
        self.llama_cpp_embed_url = (
            self.llama_cpp_embed_url if self.llama_cpp_embed_url else None
        )

        embedding_dim_env = os.getenv("EMBEDDING_DIM")
        self.embedding_dim = (
            int(embedding_dim_env) if embedding_dim_env else embedding_dim
        )
        hnsw_ef_search_env = os.getenv("HNSW_EF_SEARCH")
        self.hnsw_ef_search = (
            int(hnsw_ef_search_env) if hnsw_ef_search_env else hnsw_ef_search
        )
        logger.debug(
            "Configuração embeddings: provider=%s model=%s ollama=%s:%s llama_cpp_url=%s",
            self.embedding_provider,
            self.embedding_model,
            self.ollama_host,
            self.ollama_port,
            self.llama_cpp_embed_url,
        )

    async def get_embedding(self, texto: str) -> Optional[List[float]]:
        """Obtém embedding da query usando Ollama ou llama.cpp."""
        if self.embedding_provider == "llama_cpp" or self.llama_cpp_embed_url:
            return await self._get_embedding_llama_cpp(texto)
        return await self._get_embedding_ollama(texto)

    async def _get_embedding_ollama(self, texto: str) -> Optional[List[float]]:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{self.ollama_host}:{self.ollama_port}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": texto
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = self._extrair_embedding(data)
                    return self._validar_embedding(embedding)
                logger.error(f"Erro ao obter embedding: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Erro ao conectar com Ollama: {e}")
            return None

    async def _get_embedding_llama_cpp(self, texto: str) -> Optional[List[float]]:
        if not self.llama_cpp_embed_url:
            logger.error("URL do llama.cpp não configurada para embeddings")
            return None

        usa_openai = self.llama_cpp_embed_url.rstrip("/").endswith("/v1/embeddings")
        if usa_openai:
            payload: Dict[str, Any] = {
                "input": texto,
                "encoding_format": "float"
            }
            if self.embedding_model:
                payload["model"] = self.embedding_model
        else:
            payload = {"content": texto}
            if self.embedding_model:
                payload["model"] = self.embedding_model

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.llama_cpp_embed_url,
                    json=payload,
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    embedding = self._extrair_embedding(data)
                    return self._validar_embedding(embedding)
                logger.error(
                    f"Erro ao obter embedding no llama.cpp: {response.status_code}"
                )
                return None
        except Exception as e:
            logger.error(f"Erro ao conectar com llama.cpp: {e}")
            return None

    def _extrair_embedding(self, data: Dict[str, Any]) -> Optional[List[float]]:
        embedding = data.get("embedding")
        if embedding:
            return embedding
        dados = data.get("data")
        if isinstance(dados, list) and dados:
            return dados[0].get("embedding")
        return None

    def _validar_embedding(
        self,
        embedding: Optional[List[float]]
    ) -> Optional[List[float]]:
        if not embedding:
            logger.error("Embedding vazio retornado pelo modelo")
            return None
        if self.embedding_dim and len(embedding) != self.embedding_dim:
            logger.error(
                "Dimensão do embedding divergente do esperado: "
                f"{len(embedding)} != {self.embedding_dim}"
            )
            return None
        return embedding

    def _formatar_vetor(self, embedding: List[float]) -> str:
        # Formato aceito pelo pgvector: [1.0,2.0,3.0]
        return "[" + ",".join(str(float(valor)) for valor in embedding) + "]"

    def _calcular_ef_search(self, query: str, livro_abrev: Optional[str]) -> int:
        palavras = [p for p in query.split() if p]
        if len(palavras) > 6:
            alvo = 256
        elif livro_abrev:
            alvo = 192
        else:
            alvo = 128
        return max(self.hnsw_ef_search, alvo)

    def _montar_sql_busca(self) -> str:
        return (
            "WITH ranked AS ("
            "  SELECT "
            "    v.id, "
            "    v.embedding_2560_qwen3_4b <=> (:query_embedding)::vector AS dist "
            "  FROM versiculo v "
            "  WHERE v.versao_id = :versao_id "
            "    AND v.embedding_2560_qwen3_4b IS NOT NULL "
            "    AND ("
            "      :livro_abrev IS NULL "
            "      OR v.livro_id IN (SELECT id FROM livro WHERE abrev = :livro_abrev)"
            "    ) "
            "  ORDER BY v.embedding_2560_qwen3_4b <=> (:query_embedding)::vector "
            "  LIMIT :k "
            ") "
            "SELECT "
            "  v.id, v.texto, v.capitulo, v.numero, "
            "  l.nome AS livro_nome, l.abrev AS livro_abrev, "
            "  ver.nome AS versao_nome, ver.abrev AS versao_abrev, "
            "  r.dist "
            "FROM ranked r "
            "JOIN versiculo v ON v.id = r.id "
            "JOIN livro l ON l.id = v.livro_id "
            "JOIN versao ver ON ver.id = v.versao_id "
            "ORDER BY r.dist"
        )

    async def search(
        self,
        query: str,
        limit: int = 5,
        versao_abrev: Optional[str] = None,
        livro_abrev: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca semântica por versículos similares via pgvector."""
        if not versao_abrev:
            logger.error("Versão não informada para busca semântica")
            return []

        try:
            embedding = await self.get_embedding(query)
            if not embedding:
                return []

            vetor_consulta = self._formatar_vetor(embedding)

            with Session(engine) as session:
                versao_stmt = text(
                    "SELECT id FROM versao "
                    "WHERE abrev = :versao_abrev AND active = true"
                )
                versao_row = session.exec(
                    versao_stmt.bindparams(versao_abrev=versao_abrev)
                ).first()

                if not versao_row:
                    logger.error(
                        f"Versão '{versao_abrev}' não encontrada para busca semântica"
                    )
                    return []

                versao_id = versao_row[0]

                ef_search = self._calcular_ef_search(query, livro_abrev)
                logger.debug(
                    "Busca semântica: versao_abrev=%s versao_id=%s livro_abrev=%s "
                    "k=%s ef_search=%s",
                    versao_abrev,
                    versao_id,
                    livro_abrev,
                    limit,
                    ef_search,
                )
                session.exec(
                    text("SET hnsw.ef_search = :ef_search")
                    .bindparams(ef_search=ef_search)
                )

                sql = self._montar_sql_busca()
                params: Dict[str, Any] = {
                    "versao_id": versao_id,
                    "query_embedding": vetor_consulta,
                    "k": limit,
                    "livro_abrev": livro_abrev
                }

                rows = session.exec(text(sql).bindparams(**params)).all()
                logger.debug(
                    "Resultados (com filtro livro=%s): %s",
                    livro_abrev,
                    [row._mapping.get("id") for row in rows],
                )
                logger.debug(
                    "Retorno SQL (com filtro livro=%s): %s",
                    livro_abrev,
                    [dict(row._mapping) for row in rows],
                )
                if livro_abrev and len(rows) < limit:
                    logger.debug(
                        "Fallback sem filtro de livro (retornou %s de %s)",
                        len(rows),
                        limit,
                    )
                    params["livro_abrev"] = None
                    rows = session.exec(text(sql).bindparams(**params)).all()
                    logger.debug(
                        "Resultados (sem filtro livro): %s",
                        [row._mapping for row in rows],
                    )
                    logger.debug(
                        "Retorno SQL (sem filtro livro): %s",
                        [dict(row._mapping) for row in rows],
                    )

            formatted_results = []
            for row in rows:
                data = row._mapping
                formatted_results.append({
                    "verse_id": data["id"],
                    "text": data["texto"],
                    "livro_nome": data["livro_nome"],
                    "livro_abrev": data["livro_abrev"],
                    "capitulo": data["capitulo"],
                    "numero": data["numero"],
                    "versao_nome": data["versao_nome"],
                    "versao_abrev": data["versao_abrev"]
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []

# Instância global do serviço de busca semântica
semantic_search_service = SemanticSearch()
