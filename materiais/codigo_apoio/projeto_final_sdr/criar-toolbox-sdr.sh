#!/usr/bin/env bash
# Cria uma toolbox no Fedora com o necessário para ADALM-Pluto e RTL-SDR.
# Uso: ./criar-toolbox-sdr.sh [nome]   (padrão: sdr)

set -euo pipefail

NOME="${1:-sdr}"

# Cria a toolbox (se ainda não existir)
toolbox create -y "$NOME" 2>/dev/null || echo "Toolbox '$NOME' já existe, reutilizando."

# Instala os pacotes dentro da toolbox
toolbox run -c "$NOME" sudo dnf install -y \
    rtl-sdr \
    libiio libiio-utils \
    libad9361-iio \
    usbutils

echo "Pronto. Entre com: toolbox enter $NOME"
