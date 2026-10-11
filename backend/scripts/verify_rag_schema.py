"""Quick check that the Phase 9 RAG schema landed on the live DB."""
import os
from pathlib import Path

import psycopg2

# Load DB creds from backend/.env so no secret is hardcoded in source.
_env = Path(__file__).resolve().parents[1] / ".env"
if _env.exists():
    for _line in _env.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))

dsn = os.environ.get("PG_DSN") or (
    f"dbname={os.environ.get('DB_NAME', 'oraone')} "
    f"user={os.environ.get('DB_USER', 'oraone_admin')} "
    f"password={os.environ.get('DB_PASSWORD', '')} "
    f"host={os.environ.get('DB_HOST', '127.0.0.1')} "
    f"port={os.environ.get('DB_PORT', '15432')}"
)
c = psycopg2.connect(dsn)
cur = c.cursor()

cur.execute("select extname from pg_extension where extname='vector'")
print("vector_ext =", cur.fetchone())

cur.execute(
    "select column_name, udt_name from information_schema.columns "
    "where table_name='document_chunks' and column_name='embedding'"
)
print("embedding_col =", cur.fetchall())

cur.execute(
    "select indexname, indexdef from pg_indexes "
    "where tablename='document_chunks' and indexname='idx_document_chunks_embedding'"
)
print("hnsw_index =", cur.fetchall())

cur.execute("select version_num from alembic_version")
print("alembic_version =", cur.fetchone())

cur.close()
c.close()
