#!/bin/bash
# update_data.sh
# Rebuild and publish BmoreBuild data

set -e  # exit on first error

echo "🔹 Activating virtual environment..."
source .venv/bin/activate

echo "🔹 Rebuilding GeoJSON layers..."
python scripts/build_layers.py

echo "🔹 Staging updated data..."
git add data/
git add img/projects/
git add index.html
timestamp=$(date +"%Y-%m-%d %H:%M")
git commit -m "Data update: $timestamp"

echo "🔹 Pushing to GitHub..."
git push

echo "✅ Done. Live map should update shortly!"
