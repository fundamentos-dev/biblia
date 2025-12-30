import json
import requests
import sys
import os

# Adiciona o diretório pai ao path para importar app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models.Strongs import StrongsEntry

def import_strongs():
    # Caminho do arquivo POC local
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    POC_FILE = os.path.join(BASE_DIR, "data", "poc_strongs_greek.json")

    with Session(engine) as session:
        # Importar Grego POC
        print(f"Lendo dicionário grego POC de {POC_FILE}...")
        try:
            with open(POC_FILE, 'r', encoding='utf-8') as f:
                greek_data = json.load(f)
            
            print("Importando entradas gregas POC...")
            count = 0
            for code, data in greek_data.items():
                # Normalizar código
                strong_code = code if code.startswith("G") else f"G{code}"
                
                # Evitar duplicatas
                if session.exec(select(StrongsEntry).where(StrongsEntry.strong == strong_code)).first():
                    continue

                entry = StrongsEntry(
                    strong=strong_code,
                    lemma=data.get("lemma"),
                    transliteration=data.get("translit") or data.get("transliteration"),
                    pronunciation=data.get("pronunciation"),
                    derivation=data.get("derivation"),
                    def_short=data.get("strongs_def"),
                    def_long=data.get("kjv_def")
                )
                session.add(entry)
                count += 1
            
            session.commit()
            print(f"Concluído Grego POC: {count} entradas adicionadas.")

        except FileNotFoundError:
            print(f"Arquivo POC não encontrado: {POC_FILE}")
        except Exception as e:
            print(f"Erro ao importar grego POC: {e}")

        # (Mantendo o código original para download futuro comentado ou como fallback, mas para agora focando na POC)
        print("Importação de Hebraico ignorada na POC (sem arquivo de dados).")

if __name__ == "__main__":
    import_strongs()
