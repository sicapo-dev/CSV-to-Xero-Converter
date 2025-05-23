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
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com"
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
    "download_endpoint": False,
    "amount_prefix_logic": False,
    "folder_management": False,
    "bulk_upload": False,
    "preview_functionality": False
}

# Store tokens and IDs for use across tests
auth_token = None
file_id = None
conversion_id = None
folder_id = None

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
    global auth_token
    print("\n--- Testing /api/token endpoint ---")
    try:
        data = {
            "username": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        response = requests.post(f"{API_URL}/token", data=data)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and "access_token" in response.json():
            auth_token = response.json()["access_token"]
            test_results["token_endpoint"] = True
            print("✅ Token endpoint test passed")
            print(f"Received token: {auth_token[:10]}...")
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
    if not auth_token:
        print("❌ Cannot test /api/me without auth token")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/me", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200 and "email" in response.json():
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
    global file_id
    print("\n--- Testing /api/upload endpoint ---")
    if not auth_token:
        print("❌ Cannot test /api/upload without auth token")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        csv_data = create_test_csv()
        files = {
            'file': ('test_file.csv', csv_data, 'text/csv')
        }
        
        response = requests.post(f"{API_URL}/upload", headers=headers, files=files)
        print(f"Status code: {response.status_code}")
        print(f"Response keys: {list(response.json().keys())}")
        
        if response.status_code == 200 and "file_id" in response.json():
            file_id = response.json()["file_id"]
            test_results["upload_endpoint"] = True
            print("✅ Upload endpoint test passed")
            print(f"Received file_id: {file_id}")
            return True
        else:
            print("❌ Upload endpoint test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing upload endpoint: {str(e)}")
        return False

def test_convert_endpoint():
    """Test the convert endpoint"""
    global conversion_id
    print("\n--- Testing /api/convert endpoint ---")
    if not auth_token or not file_id:
        print("❌ Cannot test /api/convert without auth token and file_id")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        # Create a simple column mapping
        column_mapping = {
            "A": "TransactionDate",
            "B": "Reference",
            "C": "Description",
            "D": "Amount",
            "E": "Amount"  # Reference will be derived from amount
        }
        
        data = {
            'file_id': file_id,
            'column_mappings': json.dumps(column_mapping),
            'formatted_filename': f"test_formatted_{uuid.uuid4()}.csv"
        }
        
        response = requests.post(f"{API_URL}/convert", headers=headers, data=data)
        print(f"Status code: {response.status_code}")
        print(f"Response keys: {list(response.json().keys()) if response.status_code == 200 else 'Error'}")
        
        if response.status_code == 200 and "conversion_id" in response.json():
            conversion_id = response.json()["conversion_id"]
            test_results["convert_endpoint"] = True
            print("✅ Convert endpoint test passed")
            print(f"Received conversion_id: {conversion_id}")
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
    if not auth_token:
        print("❌ Cannot test /api/conversions without auth token")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/conversions", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response type: {type(response.json())}")
        print(f"Number of conversions: {len(response.json()) if isinstance(response.json(), list) else 'Not a list'}")
        
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
    if not auth_token or not conversion_id:
        print("❌ Cannot test /api/download without auth token and conversion_id")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = requests.get(f"{API_URL}/download/{conversion_id}", headers=headers)
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
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

def check_database():
    """Check the database to see if the user was created correctly"""
    print("\n--- Checking database for user ---")
    try:
        import pymongo
        client = pymongo.MongoClient('mongodb://localhost:27017')
        # Try both database names
        for db_name in ['test_database', 'xero_converter']:
            db = client[db_name]
            user = db.users.find_one({"email": TEST_USER_EMAIL})
            if user:
                print(f"User found in database '{db_name}': {user['email']}")
                print(f"User fields: {list(user.keys())}")
                if 'hashed_password' in user:
                    print("✅ User has hashed_password field")
                else:
                    print("❌ User missing hashed_password field")
                break
        else:
            print("❌ User not found in any database")
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")

def run_all_tests():
    """Run all tests in sequence"""
    print("\n=== Starting Backend API Tests ===\n")
    
    # Test status endpoint
    test_status_endpoint()
    
    # Test user registration
    test_register_endpoint()
    
    # Test token endpoint (login)
    test_token_endpoint()
    
    # If we have a token, test authenticated endpoints
    if auth_token:
        # Test me endpoint
        test_me_endpoint()
        
        # Test file upload
        test_upload_endpoint()
        
        # If file upload worked, test conversion
        if file_id:
            test_convert_endpoint()
            
            # Test conversions list
            test_conversions_endpoint()
            
            # If conversion worked, test download
            if conversion_id:
                test_download_endpoint()
    
    # Check database
    check_database()
    
    # Print summary
    print("\n=== Test Summary ===")
    for endpoint, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{endpoint}: {status}")

if __name__ == "__main__":
    run_all_tests()
