#!/bin/bash
echo "=== SER SALUD - Terapia Física API ==="
pip install -r requirements.txt -q
uvicorn main:app --host 0.0.0.0 --port ${PORT:-3000}
