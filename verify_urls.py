#!/usr/bin/env python
"""
URL Verification Script for Stories API
This script verifies all API endpoints are correctly configured and accessible.
"""
import requests
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_endpoint(method, url, data=None, headers=None, expected_status=200, description=""):
    """Test an API endpoint and return the result"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return False, f"Unsupported method: {method}"
        
        success = response.status_code == expected_status
        return success, f"{method} {url} - Status: {response.status_code} - {description}"
    except requests.exceptions.ConnectionError:
        return False, f"{method} {url} - Connection Error - {description}"
    except Exception as e:
        return False, f"{method} {url} - Error: {str(e)} - {description}"

def main():
    print("🔍 Verifying Stories API URLs...")
    print("=" * 50)
    
    # Test public endpoints (no authentication required)
    public_endpoints = [
        ("GET", f"{BASE_URL}/health/", None, None, 200, "Health Check"),
        ("GET", f"{BASE_URL}/schema/", None, None, 200, "OpenAPI Schema"),
        ("GET", f"{BASE_URL}/docs/", None, None, 200, "Swagger UI"),
        ("GET", f"{BASE_URL}/redoc/", None, None, 200, "ReDoc Documentation"),
    ]
    
    # Test authentication endpoints
    auth_endpoints = [
        ("POST", f"{BASE_URL}/token/", 
         {"email": "test@example.com", "password": "testpass123"}, 
         {"Content-Type": "application/json"}, 400, "JWT Token (will fail - no user)"),
        ("POST", f"{BASE_URL}/token/refresh/", 
         {"refresh": "invalid_token"}, 
         {"Content-Type": "application/json"}, 400, "JWT Refresh (will fail - invalid token)"),
    ]
    
    # Test protected endpoints (will fail without auth)
    protected_endpoints = [
        ("GET", f"{BASE_URL}/stories/", None, None, 401, "List Stories (requires auth)"),
        ("GET", f"{BASE_URL}/feed/", None, None, 401, "Get Feed (requires auth)"),
        ("GET", f"{BASE_URL}/me/stats/", None, None, 401, "User Stats (requires auth)"),
    ]
    
    all_endpoints = public_endpoints + auth_endpoints + protected_endpoints
    
    results = []
    for method, url, data, headers, expected_status, description in all_endpoints:
        success, message = test_endpoint(method, url, data, headers, expected_status, description)
        results.append((success, message))
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {message}")
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    
    successful = sum(1 for success, _ in results if success)
    total = len(results)
    
    print(f"✅ Successful: {successful}/{total}")
    print(f"❌ Failed: {total - successful}/{total}")
    
    if successful == total:
        print("\n🎉 All URLs are correctly configured!")
        print("\n📚 API Documentation:")
        print(f"   Swagger UI: {BASE_URL}/docs/")
        print(f"   ReDoc: {BASE_URL}/redoc/")
        print(f"   OpenAPI Schema: {BASE_URL}/schema/")
        print(f"   Health Check: {BASE_URL}/health/")
    else:
        print(f"\n⚠️  {total - successful} endpoints need attention.")
    
    print(f"\n🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return successful == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
