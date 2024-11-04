#!/bin/bash

REPO_URL="https://github.com/obsidianmd/obsidian-help.git"
REPO_DIR="data/obsidian-help"
EN_DIR="data/obsidian-help/en"
FINAL_DIR="data/obsidian"


echo "Cloning repository into $REPO_DIR without checking out..."
git clone $REPO_URL $REPO_DIR

echo "Moving $EN_DIR to $FINAL_DIR..."
mv $EN_DIR $FINAL_DIR

echo "Removing $REPO_DIR..."
rm -rf $REPO_DIR

echo "Removing non-markdown files from $FINAL_DIR..."
find $FINAL_DIR -type f ! -name "*.md" -exec rm -f {} +

echo "Repository has been successfully cloned/pulled into $REPO_DIR."
