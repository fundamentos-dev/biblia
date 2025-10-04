import logging
import httpx
import os
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    SearchRequest,
    Filter,
    FieldCondition,
    MatchValue
)
from dotenv import load_dotenv

# Carregar variáveis de ambiente com override=True
load_dotenv(override=True)

logger = logging.getLogger("api.semantic_search")

class SemanticSearch:
    def __init__(
        self,
        qdrant_host: str = "qdrant",
        qdrant_grpc_port: int = 6334,
        ollama_host: str = "ollama",
        ollama_port: int = 11434,
        collection_name: str = "biblia_ara",
        model_name: str = "mxbai-embed-large",
        embedding_dim: int = 1024
    ):
        self.qdrant_host = qdrant_host
        self.qdrant_grpc_port = qdrant_grpc_port
        self.ollama_host = ollama_host
        self.ollama_port = ollama_port
        self.collection_name = collection_name
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        
        # Obter API key do ambiente
        api_key = os.getenv("QDRANT_API_KEY")
        
        # Inicializar cliente Qdrant
        try:
            self.client = QdrantClient(
                host=qdrant_host,
                grpc_port=qdrant_grpc_port,
                api_key=api_key,
                prefer_grpc=True,
                https=False
            )
            self._ensure_collection()
        except Exception as e:
            logger.error(f"Erro ao conectar com Qdrant: {e}")
            self.client = None
            
    def _ensure_collection(self):
        """Garante que a coleção existe no Qdrant"""
        try:
            collections = self.client.get_collections()
            if self.collection_name not in [c.name for c in collections.collections]:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Coleção '{self.collection_name}' criada no Qdrant")
        except Exception as e:
            logger.error(f"Erro ao verificar/criar coleção: {e}")
            
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Obtém embedding do texto usando Ollama"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"http://{self.ollama_host}:{self.ollama_port}/api/embeddings",
                    json={
                        "model": self.model_name,
                        "prompt": text
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("embedding")
                else:
                    logger.error(f"Erro ao obter embedding: {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Erro ao conectar com Ollama: {e}")
            return None
            
    async def index_verse(
        self,
        verse_id: str,
        text: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Indexa um versículo no Qdrant"""
        if not self.client:
            return False
            
        try:
            embedding = await self.get_embedding(text)
            if not embedding:
                return False
                
            point = PointStruct(
                id=verse_id,
                vector=embedding,
                payload={
                    "text": text,
                    **metadata
                }
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao indexar versículo: {e}")
            return False
            
    async def search(
        self,
        query: str,
        limit: int = 5,
        versao_abrev: Optional[str] = None,
        livro_abrev: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca semântica por versículos similares"""
        if not self.client:
            return []
            
        try:
            # Obter embedding da query
            embedding = await self.get_embedding(query)
            if not embedding:
                return []
                
            # Construir filtro se necessário
            filter_conditions = []
            if versao_abrev:
                filter_conditions.append(
                    FieldCondition(
                        key="metadata.versao_abrev",
                        match=MatchValue(value=versao_abrev)
                    )
                )
            if livro_abrev:
                filter_conditions.append(
                    FieldCondition(
                        key="metadata.livro_abrev",
                        match=MatchValue(value=livro_abrev)
                    )
                )
                
            search_filter = Filter(must=filter_conditions) if filter_conditions else None
            
            # Realizar busca
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limit,
                query_filter=search_filter
            )
            
            # Formatar resultados
            formatted_results = []
            for result in results:
                metadata = result.payload.get("metadata", {})
                formatted_results.append({
                    "score": result.score,
                    "verse_id": result.id,
                    "text": result.payload.get("content"),
                    "livro_nome": metadata.get("livro_nome"),
                    "livro_abrev": metadata.get("livro_abrev"),
                    "capitulo": metadata.get("capitulo"),
                    "numero": metadata.get("numero"),
                    "versao_nome": metadata.get("versao_nome"),
                    "versao_abrev": metadata.get("versao_abrev")
                })
                
            return formatted_results
            
        except Exception as e:
            logger.error(f"Erro na busca semântica: {e}")
            return []
            
    async def index_all_verses(self, verses_data: List[Dict[str, Any]]) -> int:
        """Indexa múltiplos versículos em lote"""
        if not self.client:
            return 0
            
        indexed_count = 0
        for verse in verses_data:
            success = await self.index_verse(
                verse_id=verse["id"],
                text=verse["text"],
                metadata=verse["metadata"]
            )
            if success:
                indexed_count += 1
                
        logger.info(f"Indexados {indexed_count} de {len(verses_data)} versículos")
        return indexed_count

# Instância global do serviço de busca semântica
semantic_search_service = SemanticSearch()