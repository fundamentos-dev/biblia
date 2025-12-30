import os
import sys
from pathlib import Path
import psycopg2
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm
from dotenv import load_dotenv

# Adicionar o diretório raiz ao path para importar módulos da app se necessário
sys.path.append(str(Path(__file__).parent.parent))

# Carregar variáveis de ambiente
load_dotenv()

# Configurações do Banco de Dados
DB_USER = os.getenv("DB_USER", "profeta")
DB_PASS = os.getenv("DB_PASS", "eli4s")
DB_HOST = os.getenv("DB_HOST", "db-bible")
DB_NAME = os.getenv("DB_NAME", "biblia")
DB_PORT = os.getenv("DB_PORT", "5432")

DB_CONFIG = {
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASS,
    "host": DB_HOST,
    "port": DB_PORT,
}

MODEL_NAME = "Qwen/Qwen3-Embedding-4B"
BATCH_SIZE = 50
EMBEDDING_DIM = 1024

print(f"🚀 Carregando modelo {MODEL_NAME} (CPU mode)...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True)
model.eval()

@torch.no_grad()
def embed_text(texto: str) -> list:
    """
    Gera embedding de 1024 dimensões para o texto fornecido.
    Utiliza mean pooling conforme o padrão comum se o modelo não especificar.
    """
    inputs = tokenizer(
        texto,
        return_tensors="pt",
        truncation=True,
        max_length=512
    )

    outputs = model(**inputs)

    # Qwen3-Embedding pode ter um comportamento específico, mas o mean pooling
    # é uma alternativa segura se não houver instrução de pooling layer.
    last_hidden = outputs.last_hidden_state
    # Masking padding tokens for mean pooling
    attention_mask = inputs['attention_mask']
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    sum_embeddings = torch.sum(last_hidden * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    embedding = sum_embeddings / sum_mask
    
    embedding = embedding.squeeze(0)

    # Garantir dimensão 1024
    if embedding.shape[0] > EMBEDDING_DIM:
        embedding = embedding[:EMBEDDING_DIM]
    elif embedding.shape[0] < EMBEDDING_DIM:
        # Padding com zeros se for menor (improvável para este modelo)
        padding = torch.zeros(EMBEDDING_DIM - embedding.shape[0])
        embedding = torch.cat([embedding, padding])

    return embedding.cpu().numpy().astype(float).tolist()

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Conectado ao banco de dados.")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return

    while True:
        # Buscar versículos sem embedding
        cur.execute(
            """
            SELECT id, texto
            FROM versiculo
            WHERE embedding IS NULL
            ORDER BY id
            LIMIT %s
            """,
            (BATCH_SIZE,)
        )

        rows = cur.fetchall()

        if not rows:
            print("\n✨ Todos os versículos já possuem embedding ou nenhum registro encontrado.")
            break

        print(f"\n📦 Processando lote: ID {rows[0][0]} até {rows[-1][0]} ({len(rows)} registros)")

        for vid, texto in tqdm(rows, desc="Gerando embeddings", unit="ver"):
            try:
                # Limpar texto de espaços extras
                texto_limpo = texto.strip()
                if not texto_limpo:
                    continue
                    
                vec = embed_text(texto_limpo)
                
                # O pgvector aceita listas python ou strings formatadas '[1,2,3]'
                cur.execute(
                    "UPDATE versiculo SET embedding = %s WHERE id = %s",
                    (vec, vid)
                )
            except Exception as e:
                print(f"\n⚠️ Erro no versículo {vid}: {e}")
                conn.rollback() # Opcional: rollback do lote ou apenas continua
                continue

        # Commit por lote para garantir persistência e liberar locks
        conn.commit()

    cur.close()
    conn.close()
    print("🏁 Processo finalizado.")

if __name__ == "__main__":
    main()
