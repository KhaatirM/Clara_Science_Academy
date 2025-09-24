#!/bin/bash
# Build script for Render deployment
# This script runs during the build process to set up the application

echo "🔧 Building Clara Science Academy Application..."
echo "================================================"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Run database fix script
echo "🔧 Running database migration..."
python fix_production_assignment_columns_postgres.py

echo "✅ Build completed successfully!"
