#!/bin/bash
set -e

# API interna solamente — no debe ser visible desde fuera del contenedor
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 &

# Dashboard es el único punto público, escucha en el puerto que Render asigna
streamlit run src/dashboard/app.py --server.port ${PORT:-8501} --server.address 0.0.0.0