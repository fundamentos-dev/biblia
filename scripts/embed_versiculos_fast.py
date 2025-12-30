import psycopg2
import torch
import os
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

# =========================
# CONFIGURAÇÕES
# =========================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "55434")

DB_CONFIG = {
    "dbname": "biblia",
    "user": "profeta",
    "password": "eli4s",
    "host": DB_HOST,
    "port": int(DB_PORT),
}

print(f"🔧 Configuração de Banco: Host={DB_HOST}, Port={DB_PORT}")

MODEL_NAME = "Qwen/Qwen3-Embedding-4B"
BATCH_SIZE = 32 # Conservative start
EMBEDDING_DIM = 1024
MAX_LENGTH = 512

# =========================
# DEVICE (CPU / MPS)
# =========================

if torch.backends.mps.is_available():
    device = "mps"
elif torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"
    
print(f"Usando device: {device}")

# =========================
# MODELO
# =========================

print(f"Carregando modelo {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModel.from_pretrained(MODEL_NAME, trust_remote_code=True)
model.to(device)
model.eval()

@torch.no_grad()
def embed_batch(texts: list[str]) -> list[list[float]]:
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}

    outputs = model(**inputs)

    # Mean pooling em batch (check model specifics if needed, usually fine for generic embeddings)
    # Some models prefer last_hidden_state[:, 0] (CLS token) or weighted mean.
    # The previous script used mean pooling, so we stick to it for consistency.
    
    last_hidden = outputs.last_hidden_state
    attention_mask = inputs['attention_mask']
    
    # Correct mean pooling implementation considering attention mask
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    sum_embeddings = torch.sum(last_hidden * input_mask_expanded, 1)
    sum_mask = torch.clamp(input_mask_expanded.sum(1), min=1e-9)
    embeddings = sum_embeddings / sum_mask

    # Garantia de dimensão
    if embeddings.shape[1] > EMBEDDING_DIM:
        embeddings = embeddings[:, :EMBEDDING_DIM]

    return embeddings.cpu().numpy().astype(float).tolist()

# =========================
# PIPELINE
# =========================

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Conectado ao banco de dados.")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        print(f"Verifique se o container db-bible está rodando e a porta {DB_CONFIG['port']} está acessível.")
        return

    # Count total records to process
    cur.execute("SELECT COUNT(*) FROM versiculo WHERE embedding IS NULL")
    total_to_process = cur.fetchone()[0]
    print(f"Total de versículos para processar: {total_to_process}")

    if total_to_process == 0:
        print("✔ Todos os versículos já possuem embedding.")
        cur.close()
        conn.close()
        return

    with tqdm(total=total_to_process, unit="ver") as pbar:
        while True:
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
                break

            ids = [r[0] for r in rows]
            texts = [r[1] for r in rows]

            try:
                vectors = embed_batch(texts)
                data = [(vec, vid) for vec, vid in zip(vectors, ids)]

                cur.executemany(
                    "UPDATE versiculo SET embedding = %s WHERE id = %s",
                    data
                )

                conn.commit()
                pbar.update(len(rows))

            except Exception as e:
                print("Erro no batch:", e)
                conn.rollback()

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
