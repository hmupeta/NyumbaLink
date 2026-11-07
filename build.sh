#!/usr/bin/env bash
# build.sh - Runs on Render during deployment

# Exit immediately if any command fails
set -o errexit

# Install system dependencies for GeoDjango (GDAL/GEOS)
echo "Installing system dependencies..."
apt-get update && apt-get install -y gdal-bin libgdal-dev

# Install Python dependencies
echo "Installing Python requirements..."
pip install -r requirements.txt

# Collect static files for WhiteNoise
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Run migrations
echo "Running database migrations..."
python manage.py migrate
