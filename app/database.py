import os
import logging
from sqlmodel import create_engine

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Construção da URL do banco de dados a partir de variáveis de ambiente
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "postgres")
DB_HOST = os.environ.get("DB_HOST", "db")
DB_NAME = os.environ.get("DB_NAME", "biblia")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

logger.info(
    f"Conectando ao banco de dados: postgresql://{DB_USER}:***@{DB_HOST}/{DB_NAME}"
)

try:
    # Engine do SQLModel para conexões com o banco
    engine = create_engine(DATABASE_URL, echo=False)
    logger.info("Conexão com banco de dados estabelecida com sucesso")
except Exception as e:
    logger.error(f"Erro ao conectar com o banco de dados: {e}")
    raise
