#!/bin/bash
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "Virtual environment not found. Creating one..."
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
fi

cd ..
cd ..

if [ -f "set_env_vars.sh" ]; then
  echo "Setting environment variables..."
  source set_env_vars.sh
else
  echo "set_env_vars.sh not found. Terminating script."
  exit 1
fi

cd pub/fork-this-idea-slack-bot

python app.py
