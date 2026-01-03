import os
import psycopg2
import torch
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm

# =====================================================
# CONFIGURAÇÕES DE BANCO
# =====================================================

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "55434"))

DB_CONFIG = {
    "dbname": "biblia",
    "user": "profeta",
    "password": "eli4s",
    "host": DB_HOST,
    "port": DB_PORT,
}

print(f"🔧 Banco: {DB_HOST}:{DB_PORT}")

# =====================================================
# CONFIGURAÇÕES DO MODELO
# =====================================================

MODEL_NAME = "PORTULAN/serafim-900m-portuguese-pt-sentence-encoder-ir"
BATCH_SIZE = 64
MAX_LENGTH = 512
EMBEDDING_DIM = 1536

# =====================================================
# DEVICE
# =====================================================

if torch.cuda.is_available():
    device = "cuda"
elif torch.backends.mps.is_available():
    device = "mps"
else:
    device = "cpu"

print(f"🧠 Device: {device}")

# =====================================================
# MODELO
# =====================================================

print(f"📦 Carregando modelo {MODEL_NAME}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)
model.to(device)
model.eval()

# =====================================================
# FUNÇÃO DE EMBEDDING (CORRETA PARA SERAFIM)
# =====================================================

@torch.no_grad()
def embed_batch(texts: list[str]) -> list[list[float]]:
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
    ).to(device)

    outputs = model(**inputs)

    # ⚠️ Serafim é sentence-encoder → CLS pooling
    embeddings = outputs.last_hidden_state[:, 0, :]

    # Normalização L2 (OBRIGATÓRIA para cosine)
    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)

    return embeddings.cpu().numpy().astype(float).tolist()

# =====================================================
# PIPELINE
# =====================================================

def main():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Conectado ao banco")
    except Exception as e:
        print("❌ Erro ao conectar:", e)
        return

    cur.execute("""
        SELECT COUNT(*)
        FROM versiculo
        WHERE embedding_1536_serafim_900m IS NULL
    """)
    total = cur.fetchone()[0]

    print(f"📖 Versículos a processar: {total}")

    if total == 0:
        print("✔ Nada a fazer")
        return

    with tqdm(total=total, unit="vers") as pbar:
        while True:
            cur.execute(
                """
                SELECT id, texto
                FROM versiculo
                WHERE embedding_1536_serafim_900m IS NULL
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
                    """
                    UPDATE versiculo
                    SET embedding_1536_serafim_900m = %s
                    WHERE id = %s
                    """,
                    data
                )

                conn.commit()
                pbar.update(len(rows))

            except Exception as e:
                print("❌ Erro no batch:", e)
                conn.rollback()

    cur.close()
    conn.close()
    print("🏁 Finalizado")

if __name__ == "__main__":
    main()