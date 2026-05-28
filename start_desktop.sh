#!/bin/bash
# start_desktop.sh
# Script untuk menjalankan Nova Robot Assistant sebagai Aplikasi Desktop Ubuntu / Raspberry Pi

# Dapatkan direktori script ini
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "==========================================="
echo "🤖 Menjalankan Nova Robot Assistant Desktop"
echo "==========================================="

# Aktifkan virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Virtual environment (venv) tidak ditemukan! Jalankan setup terlebih dahulu."
    exit 1
fi

# Jalankan aplikasi desktop
python3 desktop_app.py
