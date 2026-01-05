import logging
import os
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
from sqlmodel import Session, text
from sentence_transformers import SentenceTransformer

from app.database import engine

# Carregar variáveis de ambiente com override=True
load_dotenv(override=True)

logger = logging.getLogger("api.semantic_search")

class SemanticSearch:
    def __init__(self):
        """
        Inicializa o serviço de busca semântica com o modelo Serafim 900m.
        
        Modelo: PORTULAN/serafim-900m-portuguese-pt-sentence-encoder-ir
        Uso: Gera embeddings de 1536 dimensões para busca vetorial.
        """
        self.model_name = "PORTULAN/serafim-900m-portuguese-pt-sentence-encoder-ir"
        logger.info(f"Carregando modelo de embedding: {self.model_name}")
        try:
            # Carrega o modelo localmente (baixa na primeira execução)
            self.model = SentenceTransformer(self.model_name)
            logger.info("Modelo carregado com sucesso.")
        except Exception as e:
            logger.error(f"FATAL: Falha ao carregar modelo {self.model_name}: {e}")
            raise e

    def _get_embedding(self, texto: str) -> List[float]:
        """Gera o embedding para o texto usando o modelo carregado."""
        try:
            # O modelo retorna um numpy array, convertemos para lista
            embedding = self.model.encode(texto)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {e}")
            raise e

    def _formatar_vetor(self, embedding: List[float]) -> str:
        """Formata a lista de floats para string de vetor do PostgreSQL."""
        return "[" + ",".join(str(float(valor)) for valor in embedding) + "]"

    def search(
        self,
        query: str,
        versao_abrev: str,
        livro_abrev: Optional[str] = None,
        limit: int = 5,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Realiza busca híbrida (Vetorial + Lexical) usando RRF (Reciprocal Rank Fusion).
        
        Lógica:
        1. CTE vector_search: Busca os top 10 por similaridade de cosseno (pgvector).
        2. CTE lexical_search: Busca os top 10 por full-text search (tsvector).
        3. CTE combined_scores: Combina os rankings usando RRF: 
           score = 1/(k + rank_vetorial) + 1/(k + rank_lexical).
        4. Retorna os top 5 resultados finais ordenados pelo score combinado.
        """
        if not versao_abrev:
            logger.error("Versão não informada para busca semântica")
            return []

        try:
            # 1. Gerar embedding da query
            embedding = self._get_embedding(query)
            vetor_consulta = self._formatar_vetor(embedding)

            with Session(engine) as session:
                # Obter ID da versão
                versao_stmt = text(
                    "SELECT id FROM versao WHERE abrev = :versao_abrev AND active = true"
                )
                versao_row = session.exec(
                    versao_stmt.bindparams(versao_abrev=versao_abrev)
                ).first()

                if not versao_row:
                    logger.warning(f"Versão '{versao_abrev}' não encontrada.")
                    return []

                versao_id = versao_row[0]

                # SQL da Busca Híbrida com RRF
                sql = """
                WITH vector_search AS (
                    SELECT 
                        v.id,
                        ROW_NUMBER() OVER (ORDER BY v.embedding_1536_serafim_900m <=> (:query_embedding)::vector) as rank_vector
                    FROM versiculo v
                    WHERE v.versao_id = :versao_id
                      AND (:livro_abrev IS NULL OR v.livro_id IN (SELECT id FROM livro WHERE abrev = :livro_abrev))
                    ORDER BY v.embedding_1536_serafim_900m <=> (:query_embedding)::vector
                    LIMIT 10
                ),
                lexical_search AS (
                    SELECT 
                        v.id,
                        ROW_NUMBER() OVER (ORDER BY ts_rank(v.tsv, plainto_tsquery('portuguese', :query)) DESC) as rank_lexical
                    FROM versiculo v
                    WHERE v.versao_id = :versao_id
                      AND (:livro_abrev IS NULL OR v.livro_id IN (SELECT id FROM livro WHERE abrev = :livro_abrev))
                      AND v.tsv @@ plainto_tsquery('portuguese', :query)
                    LIMIT 10
                ),
                combined_scores AS (
                    SELECT 
                        COALESCE(v.id, l.id) as id,
                        (COALESCE(1.0 / (:rrf_k + v.rank_vector), 0.0) + 
                         COALESCE(1.0 / (:rrf_k + l.rank_lexical), 0.0)) as score
                    FROM vector_search v
                    FULL OUTER JOIN lexical_search l ON v.id = l.id
                )
                SELECT 
                    v.id, v.texto, v.capitulo, v.numero,
                    l.nome AS livro_nome, l.abrev AS livro_abrev,
                    ver.nome AS versao_nome, ver.abrev AS versao_abrev,
                    c.score
                FROM combined_scores c
                JOIN versiculo v ON v.id = c.id
                JOIN livro l ON l.id = v.livro_id
                JOIN versao ver ON ver.id = v.versao_id
                ORDER BY c.score DESC
                LIMIT :final_limit
                """

                params = {
                    "versao_id": versao_id,
                    "query_embedding": vetor_consulta,
                    "query": query,
                    "livro_abrev": livro_abrev,
                    "rrf_k": rrf_k,
                    "final_limit": limit
                }

                rows = session.exec(text(sql).bindparams(**params)).all()
                
                # Formatar resultados
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
                        "versao_abrev": data["versao_abrev"],
                        "score": data["score"]
                    })

                return formatted_results

        except Exception as e:
            logger.error(f"Erro na busca híbrida: {e}")
            return []

# Instância global
semantic_search_service = SemanticSearch()