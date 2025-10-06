from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select

from app.database import engine
from app.models.ListaLeitura import ListaLeitura
from app.schemas.biblia import ListaLeituraResponse, ListaLeituraSchema


router = APIRouter(tags=["listas-leitura"])


@router.get("/listas-leitura", response_model=ListaLeituraResponse)
async def get_listas_leitura(
    q: Optional[str] = Query(None, description="Busca por título da lista"),
    page: int = Query(1, ge=1, description="Número da página"),
    size: int = Query(10, ge=1, le=100, description="Tamanho da página")
) -> ListaLeituraResponse:
    """
    Busca listas de leitura com filtro LIKE no título e paginação.

    Args:
        q: Termo de busca para filtrar por título (opcional)
        page: Número da página (padrão: 1)
        size: Quantidade de itens por página (padrão: 10, máximo: 100)

    Returns:
        ListaLeituraResponse: Resposta paginada com listas de leitura
    """
    try:
        with Session(engine) as session:
            # Construir query base
            stmt = select(ListaLeitura)
            
            # Aplicar filtro LIKE se fornecido
            if q:
                stmt = stmt.where(ListaLeitura.titulo.ilike(f"%{q}%"))
            
            # Contar total de registros
            count_stmt = select(ListaLeitura.id)
            if q:
                count_stmt = count_stmt.where(ListaLeitura.titulo.ilike(f"%{q}%"))
            
            total_results = session.exec(count_stmt).all()
            total = len(total_results)
            
            # Calcular offset e aplicar paginação
            offset = (page - 1) * size
            stmt = stmt.offset(offset).limit(size)
            
            # Executar query principal
            listas = session.exec(stmt).all()
            
            # Converter para schema
            items = [
                ListaLeituraSchema(
                    id=lista.id,
                    titulo=lista.titulo,
                    conteudo=lista.conteudo
                )
                for lista in listas
            ]
            
            # Calcular total de páginas
            total_pages = (total + size - 1) // size
            
            return ListaLeituraResponse(
                items=items,
                total=total,
                page=page,
                size=size,
                total_pages=total_pages
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro ao buscar listas de leitura: {str(e)}"
        )