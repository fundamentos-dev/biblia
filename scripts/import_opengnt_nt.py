import csv
import zipfile
import io
import requests
import sys
import os

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.database import engine
from app.models.Strongs import OriginalToken, StrongsEntry
from app.models.Biblia import Livro

# Mapeamento de IDs do OpenGNT (40-66) para Abreviações do nosso banco (PT)
OPENGNT_ID_MAP = {
    40: "Mt", 41: "Mc", 42: "Lc", 43: "Jo", 44: "At",
    45: "Rm", 46: "1Co", 47: "2Co", 48: "Gl", 49: "Ef",
    50: "Fp", 51: "Cl", 52: "1Ts", 53: "2Ts", 54: "1Tm",
    55: "2Tm", 56: "Tt", 57: "Fm", 58: "Hb", 59: "Tg",
    60: "1Pe", 61: "2Pe", 62: "1Jo", 63: "2Jo", 64: "3Jo",
    65: "Jd", 66: "Ap"
}

def import_opengnt():
    URL = "https://raw.githubusercontent.com/eliranwong/OpenGNT/master/OpenGNT_keyedFeatures.csv.zip"
    
    print(f"Baixando {URL}...")
    resp = requests.get(URL)
    resp.raise_for_status()
    
    with Session(engine) as session:
        # Carregar Strongs existentes para validação (set para busca rápida)
        print("Carregando lista de Strongs válidos...")
        valid_strongs = set(session.exec(select(StrongsEntry.strong)).all())
        print(f"{len(valid_strongs)} códigos Strong encontrados.")

        # Cache de IDs de livros
        livro_map_ids = {}
        for opengnt_id, abrev in OPENGNT_ID_MAP.items():
            l = session.exec(select(Livro).where(Livro.abrev == abrev)).first()
            if l:
                livro_map_ids[opengnt_id] = l.id

        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            csv_filename = [n for n in z.namelist() if n.endswith('.csv')][0]
            print(f"Lendo {csv_filename}...")
            
            with z.open(csv_filename) as f:
                content = io.TextIOWrapper(f, encoding='utf-8')
                reader = csv.reader(content, delimiter='\t')
                
                header = next(reader)
                IDX_REF = 4
                IDX_DATA = 7
                
                # Buffer para processamento
                rows_buffer = []
                
                print("Lendo CSV...")
                for row in reader:
                    rows_buffer.append(row)
                
                print(f"Total de linhas lidas: {len(rows_buffer)}")
                
                print("Processando tokens...")
                db_batch = []
                total_inserted = 0
                current_verse_key = None
                seq = 1
                
                for row in rows_buffer:
                    try:
                        # 1. Parse Referência
                        ref_raw = row[IDX_REF].strip('〔〕')
                        ref_parts = ref_raw.split('｜')
                        if len(ref_parts) < 3: continue
                        
                        opengnt_book_id = int(ref_parts[0])
                        capitulo = int(ref_parts[1])
                        versiculo = int(ref_parts[2])
                        
                        livro_id = livro_map_ids.get(opengnt_book_id)
                        if not livro_id: continue

                        # 2. Parse Dados
                        data_raw = row[IDX_DATA].strip('〔〕;')
                        data_parts = data_raw.split('=')
                        if len(data_parts) < 4: continue
                            
                        surface = data_parts[1]
                        strong_raw = data_parts[2]
                        morph = data_parts[3]
                        
                        # Limpeza do Strong
                        strong_clean = strong_raw
                        if ' ' in strong_clean: strong_clean = strong_clean.split(' ')[0]
                        if '«' in strong_clean: strong_clean = strong_clean.split('«')[0]
                        if '+' in strong_clean: strong_clean = strong_clean.split('+')[0]
                        
                        # Normalizar (G0976 -> G976)
                        if strong_clean.startswith('G') and len(strong_clean) > 2:
                            num_part = ''.join(filter(str.isdigit, strong_clean[1:]))
                            if num_part:
                                strong_clean = f"G{int(num_part)}"
                            else:
                                strong_clean = None
                        
                        # Validar se Strong existe na tabela pai
                        if strong_clean and strong_clean not in valid_strongs:
                            # Tentar fallback (ex: G1234a -> G1234)
                            # Se mesmo assim não achar, setar None para evitar IntegrityError
                            # Ou cadastrar dummy? Melhor deixar None.
                            strong_clean = None 

                        # Sequence Order
                        verse_key = (livro_id, capitulo, versiculo)
                        if verse_key != current_verse_key:
                            current_verse_key = verse_key
                            seq = 1
                        
                        token = OriginalToken(
                            livro_id=livro_id,
                            capitulo=capitulo,
                            versiculo=versiculo,
                            sequence_order=seq,
                            surface=surface,
                            strong=strong_clean,
                            morph=morph
                        )
                        seq += 1
                        
                        db_batch.append(token)
                        
                        if len(db_batch) >= 5000:
                            session.add_all(db_batch)
                            session.commit()
                            total_inserted += len(db_batch)
                            print(f"Inseridos {total_inserted} tokens...", end='\r')
                            db_batch = []
                            
                    except Exception as e:
                        pass

                if db_batch:
                    session.add_all(db_batch)
                    session.commit()
                    total_inserted += len(db_batch)
                
                print(f"\nSucesso! {total_inserted} tokens importados.")

if __name__ == "__main__":
    import_opengnt()