from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select

from app.database import engine
from app.models.Biblia import Livro
from app.models.Strongs import OriginalToken, StrongsEntry
from app.routers.biblia import obter_abreviacao_livro

router = APIRouter(tags=["strongs"])

@router.get("/biblia/verse/{livro_abrev}/{capitulo}/{versiculo}/original")
async def get_verse_original(
    livro_abrev: str,
    capitulo: int,
    versiculo: int
) -> List[OriginalToken]:
    """
    Retorna o texto original (tokens) de um versículo.
    """
    with Session(engine) as session:
        # Resolver ID do livro
        try:
            abrev_correta = obter_abreviacao_livro(livro_abrev)
            livro = session.exec(select(Livro).where(Livro.abrev == abrev_correta)).first()
        except ValueError:
            livro = None

        if not livro:
            raise HTTPException(status_code=404, detail=f"Livro '{livro_abrev}' não encontrado")

        tokens = session.exec(
            select(OriginalToken)
            .where(OriginalToken.livro_id == livro.id)
            .where(OriginalToken.capitulo == capitulo)
            .where(OriginalToken.versiculo == versiculo)
            .order_by(OriginalToken.sequence_order)
        ).all()
        
        return list(tokens)

@router.get("/strongs/{strong_code}")
async def get_strong_definition(strong_code: str) -> StrongsEntry:
    """
    Retorna a definição de um código Strong.
    """
    with Session(engine) as session:
        entry = session.get(StrongsEntry, strong_code)
        if not entry:
            raise HTTPException(status_code=404, detail=f"Código Strong '{strong_code}' não encontrado")
        return entry
