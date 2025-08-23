#!/bin/bash
set -e  # Arrêter le script en cas d'erreur

echo "[+] Installing system dependencies"
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-pip python3.10-dev python-is-python3

echo "[+] Creating virtual environment"
python3 -m venv venv

echo "[+] Activating virtual environment"
source venv/bin/activate

echo "[+] Installing build tools"
pip install --upgrade pip setuptools wheel

echo "[+] Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "[✔] Setup complete. Virtual environment is active."
echo "[i] To use the bot, run 'source venv/bin/activate' and then 'python src/main.py'."