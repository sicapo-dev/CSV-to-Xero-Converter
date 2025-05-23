#!/usr/bin/env python3
"""
Comprehensive test for the specific fixes mentioned in the review request:
1. Fixed Amount Prefix Logic
2. Fixed Folder Management 
3. Complete workflow testing
"""

import requests
import json
import uuid
import pandas as pd
from io import StringIO

# Configuration
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

# Test user credentials
TEST_USER_EMAIL = f"test_{uuid.uuid4()}@example.com"
TEST_USER_PASSWORD = "Test123!"

# Global variables
auth_token = None
test_results = {}

def setup_authentication():
    """Setup authentication for testing"""
    global auth_token
    print("=== Setting up authentication ===")
    
    # Register user
    payload = {"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    response = requests.post(f"{API_URL}/register", json=payload)
    if response.status_code != 200:
        print(f"❌ Failed to register user: {response.status_code}")
        return False
    print(f"✅ User registered: {TEST_USER_EMAIL}")
    
    # Get token
    data = {"username": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD}
    response = requests.post(f"{API_URL}/token", data=data)
    if response.status_code != 200:
        print(f"❌ Failed to get token: {response.status_code}")
        return False
    
    auth_token = response.json()["access_token"]
    print(f"✅ Token obtained: {auth_token[:20]}...")
    return True

def create_reference_test_csv():
    """Create CSV with specific reference indicators for testing amount prefix logic"""
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

def test_amount_prefix_logic():
    """Test 1: Fixed Amount Prefix Logic"""
    print("\n=== TEST 1: Amount Prefix Logic ===")
    
    if not auth_token:
        print("❌ No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    try:
        # Upload test file with reference indicators
        csv_data = create_reference_test_csv()
        files = {'file': ('reference_test.csv', csv_data, 'text/csv')}
        
        print("Uploading test file with reference indicators...")
        response = requests.post(f"{API_URL}/upload", headers=headers, files=files)
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            return False
        
        file_id = response.json()["file_id"]
        print(f"✅ File uploaded: {file_id}")
        
        # Check auto-mapping to see if transaction_type is detected
        upload_response = response.json()
        column_mapping = upload_response.get("column_mapping", {})
        print(f"Auto-detected column mapping: {column_mapping}")
        
        # Test conversion with reference-based mapping
        # The key is to use the Reference column as transaction_type
        conversion_mapping = {
            "A": "Date",
            "B": "Reference",  # This should be used for cheque number
            "C": "Description",
            "D": "Amount",
            "E": "Amount",  # Reference will be derived
            "transaction_type": "Reference"  # This is the key - use Reference column for transaction type
        }
        
        print("Converting with reference-based mapping...")
        data = {
            'file_id': file_id,
            'column_mappings': json.dumps(conversion_mapping),
            'formatted_filename': f"reference_test_formatted_{uuid.uuid4()}.csv"
        }
        
        response = requests.post(f"{API_URL}/convert", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Conversion failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        formatted_data = response.json().get("formatted_data", [])
        print(f"✅ Conversion successful: {len(formatted_data)} rows")
        
        # Analyze the results
        print("\nAnalyzing amount prefix logic:")
        expected_results = [
            {"reference": "C", "should_be_negative": True},
            {"reference": "CR", "should_be_negative": True}, 
            {"reference": "Credit", "should_be_negative": True},
            {"reference": "D", "should_be_negative": False},
            {"reference": "DB", "should_be_negative": False},
            {"reference": "Debit", "should_be_negative": False}
        ]
        
        all_correct = True
        for i, row in enumerate(formatted_data):
            if i < len(expected_results):
                expected = expected_results[i]
                amount_str = str(row.get("Amount", ""))
                
                print(f"Row {i+1}: Reference='{expected['reference']}', Amount='{amount_str}'")
                
                if expected["should_be_negative"]:
                    if not amount_str.startswith("-"):
                        print(f"  ❌ Expected negative amount for {expected['reference']}, got: {amount_str}")
                        all_correct = False
                    else:
                        print(f"  ✅ Correct negative amount for {expected['reference']}")
                else:
                    if amount_str.startswith("-"):
                        print(f"  ❌ Expected positive amount for {expected['reference']}, got: {amount_str}")
                        all_correct = False
                    else:
                        print(f"  ✅ Correct positive amount for {expected['reference']}")
        
        test_results["amount_prefix_logic"] = all_correct
        if all_correct:
            print("✅ Amount prefix logic test PASSED")
        else:
            print("❌ Amount prefix logic test FAILED")
        
        return all_correct
        
    except Exception as e:
        print(f"❌ Error in amount prefix logic test: {str(e)}")
        test_results["amount_prefix_logic"] = False
        return False

def test_folder_management():
    """Test 2: Fixed Folder Management"""
    print("\n=== TEST 2: Folder Management ===")
    
    if not auth_token:
        print("❌ No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    try:
        # Test 1: Create folder
        print("Testing folder creation...")
        data = {"name": f"Test Folder {uuid.uuid4()}"}
        response = requests.post(f"{API_URL}/folders", headers=headers, data=data)
        
        print(f"Create folder response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Create folder failed: {response.status_code}")
            print(f"Response: {response.text}")
            test_results["folder_management"] = False
            return False
        
        folder_data = response.json()
        folder_id = folder_data["id"]
        print(f"✅ Folder created: {folder_id}")
        
        # Test 2: List folders
        print("Testing folder listing...")
        response = requests.get(f"{API_URL}/folders", headers=headers)
        
        print(f"List folders response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ List folders failed: {response.status_code}")
            print(f"Response: {response.text}")
            test_results["folder_management"] = False
            return False
        
        folders = response.json()
        print(f"✅ Listed {len(folders)} folders")
        
        # Test 3: Get files in folder
        print("Testing files in folder...")
        response = requests.get(f"{API_URL}/folders/{folder_id}/files", headers=headers)
        
        print(f"Get files response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Get files in folder failed: {response.status_code}")
            print(f"Response: {response.text}")
            test_results["folder_management"] = False
            return False
        
        files = response.json()
        print(f"✅ Found {len(files)} files in folder")
        
        # Test 4: Update folder
        print("Testing folder update...")
        data = {"name": f"Updated Folder {uuid.uuid4()}"}
        response = requests.put(f"{API_URL}/folders/{folder_id}", headers=headers, data=data)
        
        print(f"Update folder response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Update folder failed: {response.status_code}")
            print(f"Response: {response.text}")
            test_results["folder_management"] = False
            return False
        
        print("✅ Folder updated successfully")
        
        # Test 5: Delete folder
        print("Testing folder deletion...")
        response = requests.delete(f"{API_URL}/folders/{folder_id}", headers=headers)
        
        print(f"Delete folder response: {response.status_code}")
        if response.status_code != 200:
            print(f"❌ Delete folder failed: {response.status_code}")
            print(f"Response: {response.text}")
            test_results["folder_management"] = False
            return False
        
        print("✅ Folder deleted successfully")
        
        test_results["folder_management"] = True
        print("✅ Folder management test PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Error in folder management test: {str(e)}")
        test_results["folder_management"] = False
        return False

def test_complete_workflow():
    """Test 3: Complete workflow with mixed reference indicators"""
    print("\n=== TEST 3: Complete Workflow ===")
    
    if not auth_token:
        print("❌ No auth token available")
        return False
    
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    try:
        # Create test CSV with mixed reference indicators
        mixed_data = {
            'TransactionDate': ['01/01/2023', '02/01/2023', '03/01/2023', '04/01/2023'],
            'RefCode': ['c', 'dr', 'CREDIT', 'debit'],
            'Narration': ['Lowercase credit', 'Lowercase debit', 'Uppercase credit', 'Lowercase debit'],
            'TransactionAmount': [100.00, 200.00, 300.00, 400.00]
        }
        df = pd.DataFrame(mixed_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_data = csv_buffer.getvalue()
        
        # Step 1: Upload file
        print("Step 1: Uploading mixed reference file...")
        files = {'file': ('mixed_test.csv', csv_data, 'text/csv')}
        response = requests.post(f"{API_URL}/upload", headers=headers, files=files)
        
        if response.status_code != 200:
            print(f"❌ Upload failed: {response.status_code}")
            return False
        
        file_id = response.json()["file_id"]
        original_data = response.json().get("original_data", [])
        formatted_data = response.json().get("formatted_data", [])
        
        print(f"✅ File uploaded: {file_id}")
        print(f"Original data rows: {len(original_data)}")
        print(f"Auto-formatted data rows: {len(formatted_data)}")
        
        # Step 2: Test preview with custom mapping
        print("Step 2: Testing preview with custom mapping...")
        custom_mapping = {
            "A": "TransactionDate",
            "B": "RefCode",
            "C": "Narration", 
            "D": "TransactionAmount",
            "E": "TransactionAmount",
            "transaction_type": "RefCode"  # Use RefCode for transaction type
        }
        
        data = {
            'file_id': file_id,
            'column_mappings': json.dumps(custom_mapping),
            'preview_only': 'true'
        }
        
        response = requests.post(f"{API_URL}/preview", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Preview failed: {response.status_code}")
            return False
        
        preview_data = response.json().get("formatted_data", [])
        print(f"✅ Preview successful: {len(preview_data)} rows")
        
        # Step 3: Convert file
        print("Step 3: Converting file...")
        data = {
            'file_id': file_id,
            'column_mappings': json.dumps(custom_mapping),
            'formatted_filename': f"mixed_test_formatted_{uuid.uuid4()}.csv"
        }
        
        response = requests.post(f"{API_URL}/convert", headers=headers, data=data)
        if response.status_code != 200:
            print(f"❌ Conversion failed: {response.status_code}")
            return False
        
        conversion_id = response.json()["conversion_id"]
        final_data = response.json().get("formatted_data", [])
        print(f"✅ Conversion successful: {conversion_id}")
        
        # Step 4: Verify amount formatting
        print("Step 4: Verifying amount formatting...")
        expected_formatting = [
            {"ref": "c", "should_be_negative": True},
            {"ref": "dr", "should_be_negative": False},
            {"ref": "CREDIT", "should_be_negative": True},
            {"ref": "debit", "should_be_negative": False}
        ]
        
        formatting_correct = True
        for i, row in enumerate(final_data):
            if i < len(expected_formatting):
                expected = expected_formatting[i]
                amount_str = str(row.get("Amount", ""))
                
                print(f"  Row {i+1}: Ref='{expected['ref']}', Amount='{amount_str}'")
                
                if expected["should_be_negative"] and not amount_str.startswith("-"):
                    print(f"    ❌ Expected negative for {expected['ref']}")
                    formatting_correct = False
                elif not expected["should_be_negative"] and amount_str.startswith("-"):
                    print(f"    ❌ Expected positive for {expected['ref']}")
                    formatting_correct = False
                else:
                    print(f"    ✅ Correct formatting for {expected['ref']}")
        
        # Step 5: Test download
        print("Step 5: Testing download...")
        response = requests.get(f"{API_URL}/download/{conversion_id}", headers=headers)
        
        if response.status_code == 200:
            # Check if it's a file response (not JSON)
            content_type = response.headers.get('content-type', '')
            if 'text/csv' in content_type or 'application/octet-stream' in content_type:
                print("✅ Download successful - received file")
                download_success = True
            else:
                print(f"❌ Download returned unexpected content type: {content_type}")
                download_success = False
        else:
            print(f"❌ Download failed: {response.status_code}")
            download_success = False
        
        # Overall workflow result
        workflow_success = formatting_correct and download_success
        test_results["complete_workflow"] = workflow_success
        
        if workflow_success:
            print("✅ Complete workflow test PASSED")
        else:
            print("❌ Complete workflow test FAILED")
        
        return workflow_success
        
    except Exception as e:
        print(f"❌ Error in complete workflow test: {str(e)}")
        test_results["complete_workflow"] = False
        return False

def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 Starting Comprehensive Testing for Review Request Fixes")
    print("=" * 60)
    
    # Setup authentication
    if not setup_authentication():
        print("❌ Authentication setup failed - cannot proceed with tests")
        return
    
    # Run the three main tests
    test_amount_prefix_logic()
    test_folder_management() 
    test_complete_workflow()
    
    # Print final summary
    print("\n" + "=" * 60)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
    
    # Overall assessment
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Fixes are working correctly!")
    else:
        print("⚠️  SOME TESTS FAILED - Issues still need to be addressed")

if __name__ == "__main__":
    run_comprehensive_tests()