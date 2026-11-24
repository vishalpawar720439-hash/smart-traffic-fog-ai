import os
import sys

# Add project root to sys.path so backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app

# Vercel Serverless Function entrypoint
