import json
import requests
import sys
import os

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models.Strongs import OriginalToken
from app.models.Biblia import Livro

def import_greek_john_1_poc():
    """
    POC: Importa João 1 do arquivo local JSON para demonstrar a funcionalidade.
    """
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    POC_FILE = os.path.join(BASE_DIR, "data", "poc_original_john_1.json")
    
    with Session(engine) as session:
        # Buscar ID de João no nosso banco
        livro_joao = session.exec(select(Livro).where(Livro.abrev == "Jo")).first()
        if not livro_joao:
            print("Livro João não encontrado no banco. Abortando.")
            return

        print(f"Lendo João 1 (Grego) POC de {POC_FILE}...")
        try:
            with open(POC_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print("Importando tokens...")
            count_verses = 0
            count_tokens = 0
            
            for verse_num_str, tokens in data.items():
                verse_num = int(verse_num_str)
                
                # Limpar tokens existentes
                existing = session.exec(
                    select(OriginalToken)
                    .where(OriginalToken.livro_id == livro_joao.id)
                    .where(OriginalToken.capitulo == 1)
                    .where(OriginalToken.versiculo == verse_num)
                ).all()
                for e in existing:
                    session.delete(e)
                
                for idx, token_data in enumerate(tokens):
                    surface = token_data.get("word") or token_data.get("text") or "???"
                    strong_raw = token_data.get("strong")
                    
                    strong_code = None
                    if strong_raw:
                        strong_code = str(strong_raw)
                    
                    morph = token_data.get("morph")

                    original_token = OriginalToken(
                        livro_id=livro_joao.id,
                        capitulo=1,
                        versiculo=verse_num,
                        sequence_order=idx + 1,
                        surface=surface,
                        strong=strong_code,
                        morph=str(morph) if morph else None
                    )
                    session.add(original_token)
                    count_tokens += 1
                
                count_verses += 1
            
            session.commit()
            print(f"Sucesso! Importados {count_tokens} tokens em {count_verses} versículos de João 1.")
            
        except FileNotFoundError:
             print(f"Arquivo POC não encontrado: {POC_FILE}")
        except Exception as e:
            print(f"Erro ao importar: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    import_greek_john_1_poc()
