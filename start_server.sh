#!/bin/bash

# Bounded Spiral Designer - Startup Script
# This script activates the virtual environment and starts the Flask backend

echo "Starting Bounded Spiral Designer Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start the Flask server
echo "Starting Flask server on http://localhost:5001"
python app.py 