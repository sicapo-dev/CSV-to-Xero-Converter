import requests
import json
import io
import pandas as pd
import time
import os
import uuid
import csv
from io import StringIO

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://89eb93da-7c1d-4fcb-ad8d-7447826c2292.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

# Test user credentials
TEST_USER_EMAIL = f"test_{uuid.uuid4()}@example.com"
TEST_USER_PASSWORD = "Test123!"

# Test results
test_results = {
    "status_endpoint": False,
    "register_endpoint": False,
    "token_endpoint": False,
    "me_endpoint": False,
    "upload_endpoint": False,
    "convert_endpoint": False,
    "conversions_endpoint": False,
    "download_endpoint": False
}

# Store tokens and IDs for use across tests
auth_token = None
file_id = None
conversion_id = None

def create_test_csv():
    """Create a sample CSV file for testing"""
    data = {
        'TransactionDate': ['01/01/2023', '02/01/2023', '03/01/2023'],
        'Reference': ['INV001', 'INV002', 'INV003'],
        'Description': ['Office Supplies', 'Software License', 'Consulting Services'],
        'Amount': [100.50, -250.75, 1000.00]
    }
    df = pd.DataFrame(data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

def test_status_endpoint():
    """Test the status endpoint"""
    print("\n--- Testing /api/status endpoint ---")
    try:
        response = requests.get(f"{API_URL}/status")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and "status" in response.json():
            test_results["status_endpoint"] = True
            print("✅ Status endpoint test passed")
            return True
        else:
            print("❌ Status endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing status endpoint: {str(e)}")
        return False

def test_register_endpoint():
    """Test the register endpoint"""
    print("\n--- Testing /api/register endpoint ---")
    try:
        payload = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        response = requests.post(f"{API_URL}/register", json=payload)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and "id" in response.json() and "email" in response.json():
            test_results["register_endpoint"] = True
            print("✅ Register endpoint test passed")
            return True
        else:
            print("❌ Register endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing register endpoint: {str(e)}")
        return False

def test_token_endpoint():
    """Test the token endpoint"""
    print("\n--- Testing /api/token endpoint ---")
    global auth_token
    try:
        # OAuth2 form data format
        payload = {
            "username": TEST_USER_EMAIL,  # OAuth2 uses username field
            "password": TEST_USER_PASSWORD
        }
        response = requests.post(f"{API_URL}/token", data=payload)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and "access_token" in response.json():
            auth_token = response.json()["access_token"]
            test_results["token_endpoint"] = True
            print("✅ Token endpoint test passed")
            return True
        else:
            print("❌ Token endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing token endpoint: {str(e)}")
        return False

def test_me_endpoint():
    """Test the me endpoint"""
    print("\n--- Testing /api/me endpoint ---")
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/me", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and "email" in response.json() and response.json()["email"] == TEST_USER_EMAIL:
            test_results["me_endpoint"] = True
            print("✅ Me endpoint test passed")
            return True
        else:
            print("❌ Me endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing me endpoint: {str(e)}")
        return False

def test_upload_endpoint():
    """Test the upload endpoint"""
    print("\n--- Testing /api/upload endpoint ---")
    global file_id
    try:
        # Create test CSV file
        csv_data = create_test_csv()
        
        # Create file-like object for upload
        files = {
            'file': ('test_data.csv', csv_data, 'text/csv')
        }
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.post(f"{API_URL}/upload", headers=headers, files=files)
        print(f"Status code: {response.status_code}")
        print(f"Response keys: {response.json().keys()}")
        
        if response.status_code == 200 and "file_id" in response.json():
            file_id = response.json()["file_id"]
            test_results["upload_endpoint"] = True
            print("✅ Upload endpoint test passed")
            print(f"Column mapping: {response.json().get('column_mapping', {})}")
            return True
        else:
            print("❌ Upload endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing upload endpoint: {str(e)}")
        return False

def test_convert_endpoint():
    """Test the convert endpoint"""
    print("\n--- Testing /api/convert endpoint ---")
    global conversion_id
    try:
        # Use the column mapping from the upload response
        column_mapping = {
            "A": "TransactionDate",
            "B": "Reference",
            "C": "Description",
            "D": "Amount",
            "E": "Amount"  # Reference is derived from amount
        }
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        payload = {
            "file_id": file_id,
            "column_mappings": json.dumps(column_mapping),
            "formatted_filename": f"test_formatted_{uuid.uuid4()}.csv"
        }
        
        response = requests.post(f"{API_URL}/convert", headers=headers, data=payload)
        print(f"Status code: {response.status_code}")
        print(f"Response keys: {response.json().keys() if response.status_code == 200 else 'Error'}")
        
        if response.status_code == 200 and "conversion_id" in response.json():
            conversion_id = response.json()["conversion_id"]
            test_results["convert_endpoint"] = True
            print("✅ Convert endpoint test passed")
            return True
        else:
            print("❌ Convert endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing convert endpoint: {str(e)}")
        return False

def test_conversions_endpoint():
    """Test the conversions endpoint"""
    print("\n--- Testing /api/conversions endpoint ---")
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/conversions", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response length: {len(response.json()) if response.status_code == 200 else 'Error'}")
        
        if response.status_code == 200 and isinstance(response.json(), list):
            test_results["conversions_endpoint"] = True
            print("✅ Conversions endpoint test passed")
            return True
        else:
            print("❌ Conversions endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing conversions endpoint: {str(e)}")
        return False

def test_download_endpoint():
    """Test the download endpoint"""
    print("\n--- Testing /api/download endpoint ---")
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/download/{conversion_id}", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else 'Error'}")
        
        if response.status_code == 200 and "file_path" in response.json():
            test_results["download_endpoint"] = True
            print("✅ Download endpoint test passed")
            return True
        else:
            print("❌ Download endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing download endpoint: {str(e)}")
        return False

def run_all_tests():
    """Run all tests in sequence"""
    print("\n=== Starting Backend API Tests ===\n")
    
    # Test status endpoint
    test_status_endpoint()
    
    # Test user registration
    if not test_register_endpoint():
        print("❌ Cannot continue testing without successful registration")
        return
    
    # Test token generation
    if not test_token_endpoint():
        print("❌ Cannot continue testing without authentication token")
        return
    
    # Test user profile
    test_me_endpoint()
    
    # Test file upload
    if not test_upload_endpoint():
        print("❌ Cannot continue testing without successful file upload")
        return
    
    # Test file conversion
    if not test_convert_endpoint():
        print("❌ Cannot continue testing without successful file conversion")
        return
    
    # Test conversion history
    test_conversions_endpoint()
    
    # Test file download
    test_download_endpoint()
    
    # Print summary
    print("\n=== Test Summary ===")
    for endpoint, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{endpoint}: {status}")

if __name__ == "__main__":
    run_all_tests()
