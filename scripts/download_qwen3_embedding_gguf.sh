#!/usr/bin/env bash
set -euo pipefail

MODEL_DIR="data/models"
MODEL_FILE="Qwen3-Embedding-4B-Q8_0.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF/resolve/main/${MODEL_FILE}?download=true"

mkdir -p "${MODEL_DIR}"
echo "Baixando ${MODEL_FILE} para ${MODEL_DIR}..."
curl -L -o "${MODEL_DIR}/${MODEL_FILE}" "${MODEL_URL}"
echo "Download concluído."
