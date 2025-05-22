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

def run_all_tests():
    """Run all tests in sequence"""
    print("\n=== Starting Backend API Tests ===\n")
    
    # Test status endpoint
    test_status_endpoint()
    
    # Test user registration
    test_register_endpoint()
    
    # Check the database to see if the user was created correctly
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
    
    # Print summary
    print("\n=== Test Summary ===")
    for endpoint, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{endpoint}: {status}")
    
    print("\n=== Authentication Issue Analysis ===")
    print("The token endpoint is failing with a 500 Internal Server Error.")
    print("Analysis of server logs shows a validation error in the UserInDB model:")
    print("- The UserInDB model inherits from User which has a required 'password' field")
    print("- When retrieving a user from the database, only 'hashed_password' is available")
    print("- This causes a validation error because 'password' is required but missing")
    print("\nRecommended fix:")
    print("1. Modify the UserInDB model to not inherit from User")
    print("2. Or make the password field optional in the User model")
    print("3. Or create a separate function to convert database data to UserInDB")

if __name__ == "__main__":
    run_all_tests()
