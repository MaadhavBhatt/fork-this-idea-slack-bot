#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

REPO_URL="https://github.com/MaadhavBhatt/fork-this-idea-slack-bot.git"
REPO_DIR="fork-this-idea-slack-bot"
PUB_DIR="pub"

# Check if pub directory exists, create if not
if [ ! -d "$PUB_DIR" ]; then
  echo "Creating $PUB_DIR directory..."
  mkdir -p "$PUB_DIR"
fi

# Navigate to pub directory
cd "$PUB_DIR" || { echo "Failed to navigate to $PUB_DIR"; exit 1; }

# Remove existing repo if it exists
if [ -d "$REPO_DIR" ]; then
  echo "Removing existing repository..."
  rm -rf "$REPO_DIR" || { echo "Failed to remove existing repository"; exit 1; }
fi

# Clone the repository
echo "Cloning repository..."
git clone "$REPO_URL" || { echo "Failed to clone repository"; exit 1; }

# Make start.sh executable
cd "$REPO_DIR"
chmod +x start.sh

cd ..
echo "Repository updated successfully."