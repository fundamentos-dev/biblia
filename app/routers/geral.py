from fastapi import APIRouter, HTTPException
from sqlmodel import Session, text
import logging

from app.database import engine

router = APIRouter(tags=["geral"])
logger = logging.getLogger(__name__)


@router.get("/hello")
async def info_hello_world():
    """
    Endpoint básico de health check do sistema.

    Returns:
        dict: Informação de status do sistema
    """
    return {
        "info": "Sistema Bíblia Self-Hosted funcionando",
        "status": "ok",
        "version": "0.1.0",
    }


@router.get("/health")
async def health_check():
    """
    Endpoint completo de health check incluindo conectividade do banco.

    Returns:
        dict: Status detalhado do sistema e dependências
    """
    try:
        # Testa conectividade do banco de dados
        with Session(engine) as session:
            session.exec(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z",  # Seria datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check falhou: {e}")
        raise HTTPException(
            status_code=503,
            detail="Serviço indisponível - falha na conectividade do banco",
        )


@router.get("/alembic_version")
async def captura_versao_alembic():
    """
    Retorna a versão atual do esquema do banco (Alembic).

    Returns:
        dict: Informação da versão do schema do banco
    """
    try:
        with Session(engine) as session:
            result = session.exec(text("SELECT version_num FROM alembic_version"))
            version = result.first()

        return {
            "schema_version": version[0] if version else "unknown",
            "migration_tool": "alembic",
        }
    except Exception as e:
        logger.error(f"Erro ao obter versão do Alembic: {e}")
        raise HTTPException(
            status_code=500, detail="Erro interno ao consultar versão do schema"
        )
