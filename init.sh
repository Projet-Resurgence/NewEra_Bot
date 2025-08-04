#!/bin/bash
set -e  # Arrêter le script en cas d'erreur

echo "[+] Installing system dependencies"
sudo apt update
sudo apt install -y python3 python-is-python3 python3-pip python3-venv

echo "[+] Creating virtual environment"
python3 -m venv venv

echo "[+] Activating virtual environment"
source venv/bin/activate

echo "[+] Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "[✔] Setup complete. Virtual environment is active."
echo "[i] To use the bot, run 'source venv/bin/activate' and then 'python src/main.py'."