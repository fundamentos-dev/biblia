import json
import requests
import sys
import os
import re

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models.Strongs import StrongsEntry

def download_and_parse_js_dict(url):
    print(f"Baixando {url}...")
    resp = requests.get(url)
    resp.raise_for_status()
    content = resp.text
    
    # O arquivo JS geralmente é "var strongsGreekDictionary = { ... };" ou "module.exports = ..."
    # Vamos tentar extrair o JSON bruto usando regex
    # Procura pelo primeiro "{" e o último "}"
    match = re.search(r'(\{[\s\S]*\})', content)
    if match:
        json_str = match.group(1)
        # Limpezas comuns em JS objects que não são JSON válido
        # Ex: chaves sem aspas. Mas o openscriptures costuma ser bem formatado.
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Tentar limpar chaves sem aspas se necessário (simplificado)
            print("Erro ao decodificar JSON direto. Tentando parsing manual simples...")
            # Fallback perigoso mas possível para JS objects simples
            return None
    return None

def import_dictionaries():
    GREEK_URL = "https://raw.githubusercontent.com/openscriptures/strongs/master/greek/strongs-greek-dictionary.js"
    HEBREW_URL = "https://raw.githubusercontent.com/openscriptures/strongs/master/hebrew/strongs-hebrew-dictionary.js"

    with Session(engine) as session:
        # 1. Grego
        data = download_and_parse_js_dict(GREEK_URL)
        if data:
            print(f"Importando {len(data)} entradas gregas...")
            count = 0
            for code, entry_data in data.items():
                strong_code = code if code.startswith("G") else f"G{code}"
                
                # Check existing
                if session.get(StrongsEntry, strong_code):
                    continue

                entry = StrongsEntry(
                    strong=strong_code,
                    lemma=entry_data.get("lemma"),
                    transliteration=entry_data.get("translit") or entry_data.get("transliteration"),
                    pronunciation=entry_data.get("pronunciation"),
                    derivation=entry_data.get("derivation"),
                    def_short=entry_data.get("strongs_def"),
                    def_long=entry_data.get("kjv_def")
                )
                session.add(entry)
                count += 1
                if count % 1000 == 0:
                    session.commit() # Commit parcial
                    print(f"Processados {count}...")
            
            session.commit()
            print("Grego concluído.")
        else:
            print("Falha ao processar dicionário grego.")

        # 2. Hebraico
        data = download_and_parse_js_dict(HEBREW_URL)
        if data:
            print(f"Importando {len(data)} entradas hebraicas...")
            count = 0
            for code, entry_data in data.items():
                strong_code = code if code.startswith("H") else f"H{code}"
                
                if session.get(StrongsEntry, strong_code):
                    continue

                entry = StrongsEntry(
                    strong=strong_code,
                    lemma=entry_data.get("lemma"),
                    transliteration=entry_data.get("translit") or entry_data.get("transliteration"),
                    pronunciation=entry_data.get("pronunciation"),
                    derivation=entry_data.get("derivation"),
                    def_short=entry_data.get("strongs_def"),
                    def_long=entry_data.get("kjv_def")
                )
                session.add(entry)
                count += 1
                if count % 1000 == 0:
                    session.commit()
                    print(f"Processados {count}...")
            
            session.commit()
            print("Hebraico concluído.")
        else:
            print("Falha ao processar dicionário hebraico.")

if __name__ == "__main__":
    import_dictionaries()
