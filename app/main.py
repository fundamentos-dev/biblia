from fastapi import FastAPI, APIRouter
from .routers import geral, biblia
from fastapi.responses import RedirectResponse

tags_metadata = [
    {
        "name": "geral",
        "description": "Operações básicas e para fins de teste que nada tem a ver com a funcionalidade do sistema",
    },
    {
        "name": "biblia",
        "description": "Operações/Endpoints para as funcinoalidades do sistema"
    },
]

app = FastAPI(
    title="Biblia Self Hosted",
    description="""
Bíblia Self-Hosted em português com intenção de uso doméstico, inicialmente criado para o Jogo da Bíblia, porém com pretenção de ser um rápido buscador desacoplado da nuvem com a facilidade de rodar fora de rastreamento.

## Onde queremos chegar 

- Fase 1: Apenas campo de busca com referências (Em Andamento)
- Fase 2: Criação de anotações: cada tag de anotação pode ter uma cor e um título, podemos ver a lista de todas elas
- Fase 3: Leitura corrida das escrituras ao selecionar um Livro, capítulo e versículo
- Fase 4: Busca avançada utilizando NLP e IA para buscar por sinônimos e contexto
""",
    version="0.1.0",
    openapi_tags=tags_metadata
)



v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(geral.router)
v1_router.include_router(biblia.router)

app.include_router(v1_router)

@app.get("/")
async def redirecionamento_pagina_inicial():
    return RedirectResponse("/docs#/biblia/captura_versiculos_biblia_por_busca_api_v1_biblia_verse_get")