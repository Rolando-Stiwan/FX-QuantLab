#!/bin/bash
set -e

# API corre solo internamente, puerto fijo 8000
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 &

# Dashboard escucha en el puerto que Render asigna via $PORT
streamlit run src/dashboard/app.py --server.port ${PORT:-8501} --server.address 0.0.0.0