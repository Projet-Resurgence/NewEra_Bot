#!/bin/bash
sudo apt install -y python3 python-is-python3 python3-pip python3-venv
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
echo "Setup complete. Use 'source venv/bin/activate' to activate the venv."