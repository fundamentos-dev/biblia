import requests
import xml.etree.ElementTree as ET
import sys
import os
import re

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models.Strongs import OriginalToken, StrongsEntry
from app.models.Biblia import Livro

# Mapeamento Arquivo XML -> Abreviação PT
# Baseado na lista de arquivos do repo morphhb/wlc
XML_BOOK_MAP = {
    "Gen.xml": "Gn", "Exod.xml": "Ex", "Lev.xml": "Lv", "Num.xml": "Nm", "Deut.xml": "Dt",
    "Josh.xml": "Js", "Judg.xml": "Jz", "Ruth.xml": "Rt", "1Sam.xml": "1Sm", "2Sam.xml": "2Sm",
    "1Kgs.xml": "1Rs", "2Kgs.xml": "2Rs", "1Chr.xml": "1Cr", "2Chr.xml": "2Cr", "Ezra.xml": "Ed",
    "Neh.xml": "Ne", "Esth.xml": "Et", "Job.xml": "Jó", "Ps.xml": "Sl", "Prov.xml": "Pv",
    "Eccl.xml": "Ec", "Song.xml": "Ct", "Isa.xml": "Is", "Jer.xml": "Jr", "Lam.xml": "Lm",
    "Ezek.xml": "Ez", "Dan.xml": "Dn", "Hos.xml": "Os", "Joel.xml": "Jl", "Amos.xml": "Am",
    "Obad.xml": "Ob", "Jonah.xml": "Jn", "Mic.xml": "Mq", "Nah.xml": "Na", "Hab.xml": "Hc",
    "Zeph.xml": "Sf", "Hag.xml": "Ag", "Zech.xml": "Zc", "Mal.xml": "Ml"
}

# Namespace XML do OSIS
NS = {'osis': 'http://www.bibletechnologies.net/2003/OSIS/namespace'}

def clean_strong(lemma_attr):
    """
    Limpa o atributo lemma para extrair o Strong principal.
    Ex: 'c/559' -> 'H559'
    Ex: '430' -> 'H430'
    Ex: 'd/216' -> 'H216'
    """
    if not lemma_attr:
        return None
    
    # Pegar a parte numérica principal
    # Geralmente é o último segmento se houver barra (prefixo/strong)
    # Mas às vezes tem sufixos.
    # Estratégia: Encontrar o primeiro número sequência de dígitos.
    
    # Se houver '/', pegar o que parece ser a raiz.
    # Em 'c/559', o 559 é a raiz.
    # Em '853', 853 é a raiz.
    
    # Remover caracteres não alfanuméricos comuns em volta
    parts = re.split(r'[/ ]', lemma_attr)
    
    strong_num = None
    for p in parts:
        # Tentar extrair dígitos de p
        digits = ''.join(filter(str.isdigit, p))
        if digits:
            strong_num = digits
            # Preferência: se o lemma original tinha '/', geralmente o strong está depois da barra
            # Mas vamos pegar o primeiro número válido encontrado das partes, 
            # ou refinar se houver lógica específica do OSHB.
            # No OSHB, 'c/559' -> c=conjunção, 559=strong.
            # Então se p for só letra, ignora.
            
            # Se encontrarmos um número, assumimos que é o Strong.
            # Caso existam múltiplos (ex: composto), pegamos o primeiro por simplicidade no MVP.
            break
            
    if strong_num:
        return f"H{int(strong_num)}" # Remover zeros à esquerda e add H
    
    return None

def import_oshb():
    BASE_URL = "https://raw.githubusercontent.com/openscriptures/morphhb/master/wlc/"
    
    with Session(engine) as session:
        # Carregar Strongs existentes para validação
        print("Carregando lista de Strongs válidos...")
        valid_strongs = set(session.exec(select(StrongsEntry.strong)).all())
        print(f"{len(valid_strongs)} códigos Strong encontrados.")

        # Cache de Livros
        livro_map = {}
        for filename, abrev in XML_BOOK_MAP.items():
            l = session.exec(select(Livro).where(Livro.abrev == abrev)).first()
            if l:
                livro_map[filename] = l.id
            else:
                print(f"Aviso: Livro {abrev} ({filename}) não encontrado no banco.")

        for filename, livro_id in livro_map.items():
            url = BASE_URL + filename
            print(f"\nBaixando {filename}...")
            
            try:
                resp = requests.get(url)
                resp.raise_for_status()
                
                # Parsing XML
                # Remover declarações de namespace e prefixos para simplificar o parsing
                xml_content = resp.text
                
                # Remover declarações xmlns
                xml_content = re.sub(r' xmlns="[^"]+"', '', xml_content)
                xml_content = re.sub(r' xmlns:\w+="[^"]+"', '', xml_content)
                xml_content = re.sub(r' xsi:\w+="[^"]+"', '', xml_content)
                
                # Remover prefixos de tags (ex: <osis:osisText> -> <osisText>)
                # Isso é um pouco arriscado se houver conteúdo com :, mas em XML OSIS é seguro nas tags
                xml_content = re.sub(r'<(/?)\w+:', r'<\1', xml_content)
                
                root = ET.fromstring(xml_content)
                
                # Iterar versículos
                # Estrutura: osisText -> div -> chapter -> verse
                # Mas chapters podem não estar explícitos em alguns OSIS, ou estar aninhados.
                # Melhor buscar todas as tags 'verse' recursivamente.
                
                verses = root.findall(".//verse")
                print(f"Processando {len(verses)} versículos em {filename}...")
                
                db_batch = []
                total_tokens = 0
                
                for verse in verses:
                    osis_id = verse.get("osisID") # Ex: Gen.1.1
                    if not osis_id: continue
                    
                    parts = osis_id.split('.')
                    if len(parts) < 3: continue
                    
                    try:
                        capitulo = int(parts[1])
                        versiculo = int(parts[2])
                    except ValueError:
                        continue
                    
                    # Iterar palavras <w>
                    words = verse.findall("w")
                    seq = 1
                    
                    for w in words:
                        surface = w.text
                        if not surface: 
                            # Às vezes o texto está misturado com segs, ou é None.
                            # OSHB costuma ter o texto dentro do w.
                            # Se tiver filhos (seg), pegar itertext
                            surface = "".join(w.itertext())
                        
                        lemma = w.get("lemma")
                        morph = w.get("morph")
                        
                        strong = clean_strong(lemma)
                        
                        # Validar Strong
                        if strong and strong not in valid_strongs:
                            strong = None
                        
                        token = OriginalToken(
                            livro_id=livro_id,
                            capitulo=capitulo,
                            versiculo=versiculo,
                            sequence_order=seq,
                            surface=surface or "",
                            strong=strong,
                            morph=morph
                        )
                        seq += 1
                        db_batch.append(token)
                    
                    # Commit em batches
                    if len(db_batch) >= 5000:
                        session.add_all(db_batch)
                        session.commit()
                        total_tokens += len(db_batch)
                        print(f"Inseridos {total_tokens} tokens...", end='\r')
                        db_batch = []
                
                # Commit final do livro
                if db_batch:
                    session.add_all(db_batch)
                    session.commit()
                    total_tokens += len(db_batch)
                
                print(f"Concluído {filename}: {total_tokens} tokens.")
                
            except Exception as e:
                print(f"Erro ao processar {filename}: {e}")

if __name__ == "__main__":
    import_oshb()
