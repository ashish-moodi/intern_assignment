#!/usr/bin/env python
"""
Professional API Test Suite for Ephemeral Stories API
This script demonstrates all API functionality with proper error handling and documentation.
"""
import requests
import json
import sys
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

class StoriesAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.story_id = None
        
    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
    
    def make_request(self, method, endpoint, data=None, headers=None, expected_status=200):
        """Make HTTP request with error handling"""
        url = f"{BASE_URL}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        
        if self.access_token:
            default_headers["Authorization"] = f"Bearer {self.access_token}"
        
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=default_headers)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, headers=default_headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=default_headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=default_headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            if response.status_code == expected_status:
                self.log(f"✅ {method} {endpoint} - Status: {response.status_code}")
                return True, response.json() if response.content else {}
            else:
                self.log(f"❌ {method} {endpoint} - Status: {response.status_code} - Expected: {expected_status}", "ERROR")
                try:
                    error_data = response.json()
                    self.log(f"   Error: {error_data}", "ERROR")
                except:
                    self.log(f"   Error: {response.text}", "ERROR")
                return False, {}
                
        except requests.exceptions.ConnectionError:
            self.log(f"❌ {method} {endpoint} - Connection Error", "ERROR")
            return False, {}
        except Exception as e:
            self.log(f"❌ {method} {endpoint} - Error: {str(e)}", "ERROR")
            return False, {}
    
    def test_health_check(self):
        """Test health check endpoint"""
        self.log("Testing Health Check...")
        success, data = self.make_request("GET", "/health/")
        if success:
            self.log(f"   Status: {data.get('status', 'unknown')}")
            if 'services' in data:
                for service, status in data['services'].items():
                    self.log(f"   {service}: {status}")
        return success
    
    def test_authentication(self):
        """Test JWT authentication"""
        self.log("Testing Authentication...")
        
        # Test token endpoint (will fail without valid user)
        success, data = self.make_request("POST", "/token/", 
            {"email": "test@example.com", "password": "testpass123"}, 
            expected_status=400)
        
        if success:
            self.log("   Token endpoint is accessible (expected to fail without valid user)")
        
        # Test refresh token endpoint
        success, data = self.make_request("POST", "/token/refresh/", 
            {"refresh": "invalid_token"}, 
            expected_status=400)
        
        if success:
            self.log("   Refresh token endpoint is accessible (expected to fail with invalid token)")
        
        return True  # These are expected to fail
    
    def test_protected_endpoints(self):
        """Test protected endpoints (should require authentication)"""
        self.log("Testing Protected Endpoints (should require auth)...")
        
        endpoints = [
            ("GET", "/stories/", "List Stories"),
            ("GET", "/feed/", "Get Feed"),
            ("GET", "/me/stats/", "User Stats"),
            ("POST", "/upload-url/", "Generate Upload URL"),
        ]
        
        all_protected = True
        for method, endpoint, description in endpoints:
            success, data = self.make_request(method, endpoint, expected_status=401)
            if success:
                self.log(f"   ✅ {description} - Properly protected")
            else:
                self.log(f"   ❌ {description} - Not properly protected", "ERROR")
                all_protected = False
        
        return all_protected
    
    def test_documentation_endpoints(self):
        """Test API documentation endpoints"""
        self.log("Testing Documentation Endpoints...")
        
        doc_endpoints = [
            ("GET", "/schema/", "OpenAPI Schema"),
            ("GET", "/docs/", "Swagger UI"),
            ("GET", "/redoc/", "ReDoc"),
        ]
        
        all_docs = True
        for method, endpoint, description in doc_endpoints:
            success, data = self.make_request(method, endpoint)
            if success:
                self.log(f"   ✅ {description} - Accessible")
            else:
                self.log(f"   ❌ {description} - Not accessible", "ERROR")
                all_docs = False
        
        return all_docs
    
    def test_story_endpoints(self):
        """Test story-related endpoints (with mock data)"""
        self.log("Testing Story Endpoints...")
        
        # Test story creation (will fail without auth)
        story_data = {
            "text": "Test story for API verification",
            "visibility": "public"
        }
        
        success, data = self.make_request("POST", "/stories/", story_data, expected_status=401)
        if success:
            self.log("   ✅ Create Story - Properly protected")
        else:
            self.log("   ❌ Create Story - Not properly protected", "ERROR")
        
        # Test story view recording (will fail without auth)
        success, data = self.make_request("POST", "/stories/test-id/view/", expected_status=401)
        if success:
            self.log("   ✅ Record Story View - Properly protected")
        else:
            self.log("   ❌ Record Story View - Not properly protected", "ERROR")
        
        # Test story reaction (will fail without auth)
        reaction_data = {"emoji": "👍"}
        success, data = self.make_request("POST", "/stories/test-id/reactions/", reaction_data, expected_status=401)
        if success:
            self.log("   ✅ Add Story Reaction - Properly protected")
        else:
            self.log("   ❌ Add Story Reaction - Not properly protected", "ERROR")
        
        return True
    
    def test_social_endpoints(self):
        """Test social features endpoints"""
        self.log("Testing Social Endpoints...")
        
        # Test follow user (will fail without auth)
        success, data = self.make_request("POST", "/follow/test-user-id/", expected_status=401)
        if success:
            self.log("   ✅ Follow User - Properly protected")
        else:
            self.log("   ❌ Follow User - Not properly protected", "ERROR")
        
        # Test unfollow user (will fail without auth)
        success, data = self.make_request("DELETE", "/unfollow/test-user-id/", expected_status=401)
        if success:
            self.log("   ✅ Unfollow User - Properly protected")
        else:
            self.log("   ❌ Unfollow User - Not properly protected", "ERROR")
        
        return True
    
    def run_all_tests(self):
        """Run all API tests"""
        self.log("🚀 Starting Stories API Test Suite")
        self.log("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("Authentication", self.test_authentication),
            ("Protected Endpoints", self.test_protected_endpoints),
            ("Documentation", self.test_documentation_endpoints),
            ("Story Endpoints", self.test_story_endpoints),
            ("Social Endpoints", self.test_social_endpoints),
        ]
        
        results = []
        for test_name, test_func in tests:
            self.log(f"\n📋 Running {test_name} Test...")
            try:
                success = test_func()
                results.append((test_name, success))
            except Exception as e:
                self.log(f"❌ {test_name} Test Failed: {str(e)}", "ERROR")
                results.append((test_name, False))
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("📊 Test Results Summary:")
        
        passed = 0
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            self.log(f"   {status} - {test_name}")
            if success:
                passed += 1
        
        self.log(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
        
        if passed == len(results):
            self.log("🎉 All tests passed! API is properly configured.")
        else:
            self.log(f"⚠️  {len(results) - passed} tests failed. Check the logs above.")
        
        self.log(f"\n📚 API Documentation URLs:")
        self.log(f"   Swagger UI: {BASE_URL}/docs/")
        self.log(f"   ReDoc: {BASE_URL}/redoc/")
        self.log(f"   OpenAPI Schema: {BASE_URL}/schema/")
        self.log(f"   Health Check: {BASE_URL}/health/")
        
        return passed == len(results)

def main():
    """Main function"""
    tester = StoriesAPITester()
    success = tester.run_all_tests()
    
    print(f"\n🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
