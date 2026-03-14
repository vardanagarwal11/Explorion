#!/bin/bash

echo "======================================================="
echo "Starting Explorion Backend API Server..."
echo "======================================================="
echo ""

# Check if running inside a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  No virtual environment detected!"
    echo "Checking for 'venv' folder..."
    
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/Scripts/activate || source venv/bin/activate
    else
        echo "❌ Error: Virtual environment 'venv' not found."
        echo "Please create a virtual environment and install requirements first."
        exit 1
    fi
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"
echo ""

python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
