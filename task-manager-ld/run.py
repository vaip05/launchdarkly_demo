#!/usr/bin/env python3
"""
Run script with optional ngrok tunnel.
Usage: python run.py [--ngrok]
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def run_with_ngrok():
    from pyngrok import ngrok, conf
    
    ngrok_token = os.getenv("NGROK_AUTHTOKEN", "")
    if ngrok_token:
        conf.get_default().auth_token = ngrok_token
    
    print("Starting ngrok tunnel...")
    tunnel = ngrok.connect(5000)
    print(f"\nPublic URL: {tunnel.public_url}")
    print("Share this URL to access your app from anywhere!\n")
    
    os.system("python app.py")


def run_local():
    os.system("python app.py")


if __name__ == "__main__":
    if "--ngrok" in sys.argv or "-n" in sys.argv:
        run_with_ngrok()
    else:
        run_local()
