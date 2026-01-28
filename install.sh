#!/bin/bash

# Install script for WordPress RAG system

echo "========================================"
echo "WordPress RAG System - Installation"
echo "========================================"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "ERROR: pip3 not found. Please install Python 3.9+"
    exit 1
fi

echo ""
echo "Installing Python dependencies..."
echo "This may take a few minutes..."
echo ""

pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "✓ Installation Complete!"
    echo "========================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. (Optional) Start local Qdrant:"
    echo "   docker run -p 6333:6333 qdrant/qdrant"
    echo ""
    echo "2. Ingest your WordPress data:"
    echo "   python3 main.py ingest --recreate"
    echo ""
    echo "3. Start searching:"
    echo "   python3 main.py search 'your query'"
    echo ""
else
    echo ""
    echo "========================================"
    echo "✗ Installation Failed"
    echo "========================================"
    echo ""
    echo "Please check the error messages above."
    exit 1
fi
