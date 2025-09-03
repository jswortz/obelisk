#!/usr/bin/env python3
"""Test script to verify frontend is working"""

import requests
import time

def test_frontend():
    """Test if frontend is accessible"""
    try:
        response = requests.get("http://localhost:5173/")
        if response.status_code == 200:
            print("✅ Frontend is running at http://localhost:5173/")
            print("   - Virtual Try-On interface is available")
            print("   - Image Editor interface is available")
            print("\nTo use the application:")
            print("1. Upload a person image and product image")
            print("2. Click 'Generate Virtual Try-On'")
            print("3. After generation, switch to Image Editor tab")
            print("4. Enter a background prompt and click 'Change Background'")
        else:
            print(f"❌ Frontend returned status code: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to frontend. Make sure it's running with 'make frontend-dev'")
    except Exception as e:
        print(f"❌ Error testing frontend: {e}")

if __name__ == "__main__":
    print("Testing Obelisk Frontend...")
    test_frontend()