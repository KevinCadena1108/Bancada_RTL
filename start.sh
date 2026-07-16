#!/bin/bash
# Sobe o avaliador. Rodar no WSL/Linux, NUNCA em /mnt/c.
set -e

cd "$(dirname "$0")"

# Ambiente virtual (uma vez)
if [ ! -d venv ]; then
    echo "==> Criando ambiente virtual"
    python3 -m venv venv
fi
source venv/bin/activate

echo "==> Instalando dependencias"
pip install -q -r requirements.txt

# Checa Verilator antes de subir
if ! command -v verilator >/dev/null 2>&1; then
    echo "!! Verilator nao encontrado. Instale: sudo apt install verilator"
    exit 1
fi

echo ""
echo "==> Servidor no ar em http://127.0.0.1:5000"
echo "    (Ctrl+C para parar)"
echo ""
python3 app.py
