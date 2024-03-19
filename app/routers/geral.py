from fastapi import APIRouter

router = APIRouter(tags=["geral"])


@router.get("/hello")
async def info_hello_world():
    return {"info": "Teste de funcionamento do sistema"}


@router.get("/alembic_version")
async def captura_versao_alembic():
    return {"info": "Teste de funcionamento do sistema"}