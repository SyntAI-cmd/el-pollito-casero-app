"""Escribe apps/api/openapi.json para que packages/api-client genere el cliente TS."""

import json
from pathlib import Path

from app.main import app

destino = Path(__file__).resolve().parent.parent / "openapi.json"
destino.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"OpenAPI escrito en {destino}")
