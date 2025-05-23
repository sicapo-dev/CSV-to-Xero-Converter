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

def create_reference_test_csv():
    """Create a CSV file with reference column containing debit/credit indicators"""
    data = {
        'Date': ['01/01/2023', '02/01/2023', '03/01/2023', '04/01/2023', '05/01/2023', '06/01/2023'],
        'Reference': ['C', 'CR', 'Credit', 'D', 'DB', 'Debit'],
        'Description': ['Credit Transaction', 'Credit Entry', 'Credit Payment', 'Debit Transaction', 'Debit Entry', 'Debit Payment'],
        'Amount': [100.50, 250.75, 1000.00, 150.25, 300.00, 500.00]
    }
    df = pd.DataFrame(data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

def create_mixed_reference_csv():
    """Create a CSV file with mixed reference indicators"""
    data = {
        'Date': ['01/01/2023', '02/01/2023', '03/01/2023', '04/01/2023'],
        'Reference': ['c', 'dr', 'CREDIT', 'debit'],
        'Description': ['Lowercase credit', 'Lowercase debit', 'Uppercase credit', 'Lowercase debit'],
        'Amount': [100.00, 200.00, 300.00, 400.00]
    }
    df = pd.DataFrame(data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

def create_bulk_test_files():
    """Create multiple test files for bulk upload testing"""
    files = []
    
    # File 1: Basic CSV
    data1 = {
        'Date': ['01/01/2023', '02/01/2023'],
        'Ref': ['REF001', 'REF002'],
        'Desc': ['Test 1', 'Test 2'],
        'Amount': [100.00, 200.00]
    }
    df1 = pd.DataFrame(data1)
    csv_buffer1 = StringIO()
    df1.to_csv(csv_buffer1, index=False)
    files.append(('file1.csv', csv_buffer1.getvalue()))
    
    # File 2: CSV with reference indicators
    data2 = {
        'Date': ['03/01/2023', '04/01/2023'],
        'Reference': ['C', 'D'],
        'Description': ['Credit entry', 'Debit entry'],
        'Amount': [300.00, 400.00]
    }
    df2 = pd.DataFrame(data2)
    csv_buffer2 = StringIO()
    df2.to_csv(csv_buffer2, index=False)
    files.append(('file2.csv', csv_buffer2.getvalue()))
    
    return files

def test_amount_prefix_logic():
    """Test the amount prefix logic with reference-based formatting"""
    print("\n--- Testing Amount Prefix Logic ---")
    if not auth_token:
        print("❌ Cannot test amount prefix logic without auth token")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test with reference indicators
        csv_data = create_reference_test_csv()
        files = {
            'file': ('reference_test.csv', csv_data, 'text/csv')
        }
        
        # Upload file
        response = requests.post(f"{API_URL}/upload", headers=headers, files=files)
        if response.status_code != 200:
            print(f"❌ Failed to upload reference test file: {response.status_code}")
            return False
        
        ref_file_id = response.json()["file_id"]
        print(f"Uploaded reference test file with ID: {ref_file_id}")
        
        # Test conversion with reference-based mapping
        column_mapping = {
            "A": "Date",
            "B": "Reference", 
            "C": "Description",
            "D": "Amount",
            "E": "Amount",  # Reference will be derived from amount
            "transaction_type": "Reference"  # Use Reference column for transaction type detection
        }
        
        data = {
            'file_id': ref_file_id,
            'column_mappings': json.dumps(column_mapping),
            'formatted_filename': f"reference_test_formatted_{uuid.uuid4()}.csv"
        }
        
        response = requests.post(f"{API_URL}/convert", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to convert reference test file: {response.status_code}")
            return False
        
        formatted_data = response.json().get("formatted_data", [])
        print(f"Converted {len(formatted_data)} rows")
        
        # Check amount formatting based on reference values
        expected_results = [
            {"reference": "C", "original_amount": 100.50, "should_be_negative": True},
            {"reference": "CR", "original_amount": 250.75, "should_be_negative": True},
            {"reference": "Credit", "original_amount": 1000.00, "should_be_negative": True},
            {"reference": "D", "original_amount": 150.25, "should_be_negative": False},
            {"reference": "DB", "original_amount": 300.00, "should_be_negative": False},
            {"reference": "Debit", "original_amount": 500.00, "should_be_negative": False}
        ]
        
        all_correct = True
        for i, row in enumerate(formatted_data):
            if i < len(expected_results):
                expected = expected_results[i]
                amount_str = str(row.get("Amount", ""))
                
                print(f"Row {i+1}: Reference='{expected['reference']}', Amount='{amount_str}'")
                
                if expected["should_be_negative"]:
                    if not amount_str.startswith("-"):
                        print(f"❌ Expected negative amount for {expected['reference']}, got: {amount_str}")
                        all_correct = False
                    else:
                        print(f"✅ Correct negative amount for {expected['reference']}")
                else:
                    if amount_str.startswith("-"):
                        print(f"❌ Expected positive amount for {expected['reference']}, got: {amount_str}")
                        all_correct = False
                    else:
                        print(f"✅ Correct positive amount for {expected['reference']}")
        
        if all_correct:
            test_results["amount_prefix_logic"] = True
            print("✅ Amount prefix logic test passed")
            return True
        else:
            print("❌ Amount prefix logic test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing amount prefix logic: {str(e)}")
        return False

def test_folder_management():
    """Test folder management endpoints"""
    global folder_id
    print("\n--- Testing Folder Management ---")
    if not auth_token:
        print("❌ Cannot test folder management without auth token")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test creating a folder
        print("Testing folder creation...")
        data = {"name": f"Test Folder {uuid.uuid4()}"}
        response = requests.post(f"{API_URL}/folders", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to create folder: {response.status_code}")
            return False
        
        folder_id = response.json()["id"]
        print(f"✅ Created folder with ID: {folder_id}")
        
        # Test listing folders
        print("Testing folder listing...")
        response = requests.get(f"{API_URL}/folders", headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to list folders: {response.status_code}")
            return False
        
        folders = response.json()
        print(f"✅ Listed {len(folders)} folders")
        
        # Test updating folder
        print("Testing folder update...")
        data = {"name": f"Updated Test Folder {uuid.uuid4()}"}
        response = requests.put(f"{API_URL}/folders/{folder_id}", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to update folder: {response.status_code}")
            return False
        
        print("✅ Updated folder successfully")
        
        # Test getting files in folder (should be empty)
        print("Testing files in folder...")
        response = requests.get(f"{API_URL}/folders/{folder_id}/files", headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to get files in folder: {response.status_code}")
            return False
        
        files_in_folder = response.json()
        print(f"✅ Found {len(files_in_folder)} files in folder")
        
        # Test uploading a file to the folder
        print("Testing file upload to folder...")
        csv_data = create_test_csv()
        files = {
            'file': ('folder_test.csv', csv_data, 'text/csv')
        }
        data = {"folder_id": folder_id}
        
        response = requests.post(f"{API_URL}/upload", headers=headers, files=files, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to upload file to folder: {response.status_code}")
            return False
        
        folder_file_id = response.json()["file_id"]
        print(f"✅ Uploaded file to folder with ID: {folder_file_id}")
        
        # Test moving file between folders
        print("Testing file move...")
        data = {"file_id": folder_file_id, "target_folder_id": "root"}
        response = requests.post(f"{API_URL}/files/move", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to move file: {response.status_code}")
            return False
        
        print("✅ Moved file successfully")
        
        # Test deleting folder (should work now that file is moved)
        print("Testing folder deletion...")
        response = requests.delete(f"{API_URL}/folders/{folder_id}", headers=headers)
        if response.status_code != 200:
            print(f"❌ Failed to delete folder: {response.status_code}")
            return False
        
        print("✅ Deleted folder successfully")
        
        test_results["folder_management"] = True
        print("✅ Folder management test passed")
        return True
        
    except Exception as e:
        print(f"❌ Error testing folder management: {str(e)}")
        return False

def test_bulk_upload():
    """Test bulk file upload functionality"""
    print("\n--- Testing Bulk Upload ---")
    if not auth_token:
        print("❌ Cannot test bulk upload without auth token")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Create test files
        test_files = create_bulk_test_files()
        
        # Prepare files for upload
        files = []
        for filename, content in test_files:
            files.append(('files', (filename, content, 'text/csv')))
        
        # Upload files
        response = requests.post(f"{API_URL}/bulk-upload", headers=headers, files=files)
        if response.status_code != 200:
            print(f"❌ Failed bulk upload: {response.status_code}")
            return False
        
        results = response.json().get("results", [])
        print(f"Bulk upload results: {len(results)} files processed")
        
        # Check results
        successful_uploads = 0
        for result in results:
            if result.get("success", False):
                successful_uploads += 1
                print(f"✅ {result['filename']}: Success")
            else:
                print(f"❌ {result['filename']}: {result.get('error', 'Unknown error')}")
        
        if successful_uploads == len(test_files):
            test_results["bulk_upload"] = True
            print("✅ Bulk upload test passed")
            return True
        else:
            print(f"❌ Bulk upload test failed: {successful_uploads}/{len(test_files)} successful")
            return False
            
    except Exception as e:
        print(f"❌ Error testing bulk upload: {str(e)}")
        return False

def test_preview_functionality():
    """Test the preview endpoint functionality"""
    print("\n--- Testing Preview Functionality ---")
    if not auth_token or not file_id:
        print("❌ Cannot test preview functionality without auth token and file_id")
        return False
    
    try:
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        # Test preview with different column mappings
        print("Testing preview with custom column mapping...")
        
        # Create a custom column mapping
        column_mapping = {
            "A": "TransactionDate",
            "B": "Reference",
            "C": "Description", 
            "D": "Amount",
            "E": "Amount"
        }
        
        data = {
            'file_id': file_id,
            'column_mappings': json.dumps(column_mapping),
            'preview_only': 'true'
        }
        
        response = requests.post(f"{API_URL}/preview", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to get preview: {response.status_code}")
            return False
        
        preview_data = response.json()
        print(f"✅ Preview returned {len(preview_data.get('formatted_data', []))} rows")
        
        # Test preview with different mapping
        print("Testing preview with modified column mapping...")
        
        modified_mapping = {
            "A": "Reference",  # Swap columns
            "B": "TransactionDate",
            "C": "Description",
            "D": "Amount",
            "E": "Amount"
        }
        
        data = {
            'file_id': file_id,
            'column_mappings': json.dumps(modified_mapping),
            'preview_only': 'true'
        }
        
        response = requests.post(f"{API_URL}/preview", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Failed to get modified preview: {response.status_code}")
            return False
        
        modified_preview = response.json()
        print(f"✅ Modified preview returned {len(modified_preview.get('formatted_data', []))} rows")
        
        # Verify that the preview data changed
        original_first_row = preview_data.get('formatted_data', [{}])[0] if preview_data.get('formatted_data') else {}
        modified_first_row = modified_preview.get('formatted_data', [{}])[0] if modified_preview.get('formatted_data') else {}
        
        if original_first_row.get('Date') != modified_first_row.get('Date'):
            print("✅ Preview correctly updated when column mapping changed")
            test_results["preview_functionality"] = True
            print("✅ Preview functionality test passed")
            return True
        else:
            print("❌ Preview did not update when column mapping changed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing preview functionality: {str(e)}")
        return False

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
        
        # Test new functionality requested in review
        print("\n=== Testing Specific Review Request Features ===")
        
        # Test amount prefix logic with reference columns
        test_amount_prefix_logic()
        
        # Test folder management
        test_folder_management()
        
        # Test bulk upload
        test_bulk_upload()
        
        # Test preview functionality
        test_preview_functionality()
    
    # Check database
    check_database()
    
    # Print summary
    print("\n=== Test Summary ===")
    for endpoint, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{endpoint}: {status}")

if __name__ == "__main__":
    run_all_tests()
