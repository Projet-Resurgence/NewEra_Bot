#!/bin/bash
set -e  # Arrêter le script en cas d'erreur

echo "[+] Installing system dependencies"
sudo apt update
sudo apt install -y python3.12 python3-venv python3-pip python3-dev python-is-python3

echo "[+] Installing web browsing packages"
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install -y ./google-chrome-stable_current_amd64.deb
sudo rm -rf ./google-chrome-stable_current_amd64.deb

echo "[+] Creating virtual environment"
python3 -m venv venv

echo "[+] Activating virtual environment"
source venv/bin/activate

echo "[+] Installing build tools"
pip3 install --upgrade pip setuptools wheel

echo "[+] Installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "[✔] Setup complete. Virtual environment is active."
echo "[i] To use the bot, run 'source venv/bin/activate' and then 'python src/main.py'."
