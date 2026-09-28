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

# Planilha (Google Apps Script): a URL do webhook fica em webhook.env, que
# NAO vai para o git (contem um endereco que escreve na sua planilha).
# Crie o arquivo webhook.env ao lado deste com a linha:
#   export GSHEET_WEBHOOK="https://script.google.com/macros/s/SEU_ID/exec"
[ -f webhook.env ] && source webhook.env

echo ""
echo "==> Servidor no ar em http://127.0.0.1:5000"
if [ -n "$GSHEET_WEBHOOK" ]; then
    echo "    Planilha conectada (envio automatico ligado)"
fi
echo "    (Ctrl+C para parar)"
echo ""
python3 app.py
