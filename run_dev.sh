#!/bin/bash
# Root check removed since we now have a socket-based fallback

source venv310/bin/activate
source .env
export API_PORT=5001  # Use a different port for development
cd api
python app.py
