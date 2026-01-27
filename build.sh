#!/bin/bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install -r backend/requirements.txt

# Install Node dependencies and build frontend
cd frontend
npm install
npm run build
cd ..
