import os
import numpy as np
import psycopg2
import psycopg2.extras
from tqdm import tqdm
import mlx.core as mx
from concurrent.futures import ThreadPoolExecutor

from pgvector.psycopg2 import register_vector
from mlx_embeddings.utils import load

# =========================
# CONFIGURAÇÕES
# =========================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "55434"))

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "biblia"),
    "user": os.getenv("DB_USER", "profeta"),
    "password": os.getenv("DB_PASSWORD", "eli4s"),
    "host": DB_HOST,
    "port": DB_PORT,
}

print(f"🔧 Configuração de Banco: Host={DB_HOST}, Port={DB_PORT}")

MLX_MODEL_NAME = os.getenv(
    "EMBEDDING_MODEL",
    "mlx-community/Qwen3-Embedding-4B-4bit-DWQ",
)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "512"))  # ✅ solicitado: 512
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "2560"))
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "512"))

TARGET_COLUMN = os.getenv("TARGET_COLUMN", "embedding_2560_qwen3_4b")

# =========================
# SQL
# =========================

COUNT_SQL = f"SELECT COUNT(*) FROM versiculo WHERE {TARGET_COLUMN} IS NULL"

SELECT_BATCH_SQL = f"""
SELECT id, texto
FROM versiculo
WHERE {TARGET_COLUMN} IS NULL
ORDER BY id
LIMIT %s
"""

UPDATE_SQL = f"""
UPDATE versiculo AS v
SET {TARGET_COLUMN} = data.embedding::vector
FROM (VALUES %s) AS data(id, embedding)
WHERE v.id = data.id
"""

# =========================
# EMBEDDING (MLX)
# =========================

def embed_batch(model, tokenizer, texts: list[str]) -> np.ndarray:
    inputs = tokenizer.batch_encode_plus(
        texts,
        return_tensors="mlx",
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
    )

    outputs = model(
        inputs["input_ids"],
        attention_mask=inputs.get("attention_mask"),
    )

    emb = outputs.text_embeds  # (B, D) - pode vir em bf16
    emb = emb.astype(mx.float32)
    mx.eval(emb)

    if EMBEDDING_DIM < emb.shape[1]:
        emb = emb[:, :EMBEDDING_DIM]
        mx.eval(emb)

    return np.array(emb, dtype=np.float32)

# =========================
# PREFETCH
# =========================

def fetch_batch(fetch_conn) -> list[tuple[int, str]]:
    with fetch_conn.cursor() as cur:
        cur.execute(SELECT_BATCH_SQL, (BATCH_SIZE,))
        return cur.fetchall()

# =========================
# PIPELINE
# =========================

def main():
    print(f"📦 Modelo MLX: {MLX_MODEL_NAME}")
    print(f"🧠 EMBEDDING_DIM={EMBEDDING_DIM} | MAX_LENGTH={MAX_LENGTH} | BATCH_SIZE={BATCH_SIZE}")
    print(f"🧾 Coluna alvo: {TARGET_COLUMN}")

    # Carrega modelo/tokenizer MLX
    mlx_model, mlx_tokenizer = load(MLX_MODEL_NAME)

    # DB: 1 conexão writer + 1 conexão reader (prefetch)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn)
        cur = conn.cursor()
        print("✅ Conectado ao banco de dados (writer).")

        fetch_conn = psycopg2.connect(**DB_CONFIG)
        fetch_conn.set_session(readonly=True, autocommit=True)
        print("✅ Conectado ao banco de dados (prefetch/reader).")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")
        return

    # Count total records to process
    cur.execute(COUNT_SQL)
    total_to_process = cur.fetchone()[0]
    print(f"Total de versículos para processar: {total_to_process}")

    if total_to_process == 0:
        print("✔ Todos os versículos já possuem embedding.")
        cur.close()
        conn.close()
        fetch_conn.close()
        return

    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fetch_batch, fetch_conn)  # prefetch inicial

        with tqdm(total=total_to_process, unit="ver") as pbar:
            while True:
                rows = future.result()
                if not rows:
                    break

                # dispara prefetch do próximo batch o quanto antes
                future = ex.submit(fetch_batch, fetch_conn)

                ids = [r[0] for r in rows]
                texts = [(r[1] or "") for r in rows]

                try:
                    vectors = embed_batch(mlx_model, mlx_tokenizer, texts)  # (B, D)

                    values = [(vid, vectors[i]) for i, vid in enumerate(ids)]
                    psycopg2.extras.execute_values(
                        cur,
                        UPDATE_SQL,
                        values,
                        template="(%s, %s)",
                        page_size=len(values),
                    )

                    conn.commit()
                    pbar.update(len(rows))

                except Exception as e:
                    print("Erro no batch:", e)
                    conn.rollback()

    cur.close()
    conn.close()
    fetch_conn.close()

if __name__ == "__main__":
    main()