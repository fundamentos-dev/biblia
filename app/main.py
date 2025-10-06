import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import RedirectResponse, HTMLResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .routers import geral, biblia, listas_leitura

# Configuração de templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Metadados para documentação da API
tags_metadata = [
    {
        "name": "geral",
        "description": "Endpoints de sistema: health checks, versão e status geral",
    },
    {
        "name": "biblia",
        "description": "Endpoints principais: busca de versículos, livros e navegação bíblica",
    },
    {
        "name": "listas-leitura",
        "description": "Endpoints para gerenciar listas de leitura bíblica",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação FastAPI."""
    logger.info("🚀 Iniciando Bíblia Self-Hosted API")
    logger.info("📖 Sistema de busca bíblica carregado")
    yield
    logger.info("🔄 Encerrando Bíblia Self-Hosted API")


# Configuração da aplicação FastAPI
app = FastAPI(
    title="Bíblia Self-Hosted API",
    description="""
## 📖 Bíblia Self-Hosted

API para busca e navegação em textos bíblicos, com foco em uso doméstico e privacidade.

### ✨ Funcionalidades Principais

- **Busca de versículos**: Parse inteligente de referências bíblicas
- **Navegação estruturada**: Acesso por livros, capítulos e versículos
- **Múltiplos formatos**: Suporte a diferentes padrões de referência
- **Self-hosted**: Execução local, sem dependência de serviços externos

### 🎯 Roadmap

- **✅ Fase 1**: Busca básica com referências (Concluída)
- **🔄 Fase 2**: Sistema de anotações com tags coloridas
- **📋 Fase 3**: Leitura sequencial de passagens
- **🤖 Fase 4**: Busca semântica com IA/NLP

### 📊 Formatos de Busca Suportados

- `João 3:16` - Versículo único
- `João 3:16-18` - Faixa de versículos
- `João 3:16,17,20` - Múltiplos versículos
- `João 3:16; Mateus 5:1` - Múltiplos livros
""",
    version="0.2.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
    contact={
        "name": "Bíblia Self-Hosted",
        "url": "https://github.com/user/biblia-self-hosted",
    },
    license_info={"name": "MIT License", "url": "https://opensource.org/licenses/MIT"},
)

# Configuração de CORS para desenvolvimento
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Router versionado para API
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
v1_router.include_router(geral.router)
v1_router.include_router(biblia.router)
v1_router.include_router(listas_leitura.router)



app.include_router(v1_router)

# Montar arquivos estáticos se o diretório existir
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def pagina_inicial(request: Request):
    """
    Página inicial com interface de busca bíblica estilo terminal.

    Returns:
        HTMLResponse: Template HTML renderizado
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api", include_in_schema=False)
async def api_info():
    """
    Informações básicas da API.

    Returns:
        dict: Metadados da API
    """
    return {
        "name": "Bíblia Self-Hosted API",
        "version": "0.2.0",
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt():
    """
    Robots.txt para controle de indexação de bots de busca.
    """
    content = """User-agent: *
Allow: /

# Sitemap
Sitemap: https://biblia.filipelopes.me/sitemap.xml

# Crawl delay
Crawl-delay: 1

# Disallow admin/internal paths
Disallow: /admin
Disallow: /api/"""
    return content


@app.get("/sitemap.xml", response_class=Response, include_in_schema=False)
async def sitemap_xml():
    """
    Sitemap XML para motores de busca.
    """
    content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://biblia.filipelopes.me/</loc>
        <lastmod>2024-01-01</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>https://biblia.filipelopes.me/docs</loc>
        <lastmod>2024-01-01</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>
</urlset>"""
    return Response(content=content, media_type="application/xml")
