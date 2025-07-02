#!/bin/bash
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "Virtual environment not found. Creating one..."
  python -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
fi

python app.py > ~/ftibot/bot.log 2>&1
