#!/usr/bin/env python3

import requests
import json
import csv
import io
import os
from datetime import datetime

# Configuration
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com/api"

def create_test_csv_with_reference():
    """Create a test CSV file with Reference column containing Credit/Debit values"""
    test_data = [
        ["Date", "Description", "Amount", "Reference", "Cheque No"],
        ["01/01/2024", "Office Supplies", "150.00", "Debit", "CHQ001"],
        ["02/01/2024", "Sales Revenue", "500.00", "Credit", "CHQ002"],
        ["03/01/2024", "Rent Payment", "1200.00", "D", "CHQ003"],
        ["04/01/2024", "Customer Refund", "75.00", "C", "CHQ004"],
        ["05/01/2024", "Equipment Purchase", "2500.00", "DB", "CHQ005"],
        ["06/01/2024", "Interest Income", "25.00", "CR", "CHQ006"],
        ["07/01/2024", "Utility Bill", "300.00", "Debit", "CHQ007"],
        ["08/01/2024", "Service Income", "800.00", "Credit", "CHQ008"]
    ]
    
    # Create CSV content
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    writer.writerows(test_data)
    csv_content.seek(0)
    
    return csv_content.getvalue()

def register_test_user():
    """Register a test user for authentication"""
    user_data = {
        "email": f"test_preview_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BACKEND_URL}/register", json=user_data)
    if response.status_code == 200:
        print(f"✅ User registered successfully: {user_data['email']}")
        return user_data
    else:
        print(f"❌ Failed to register user: {response.status_code} - {response.text}")
        return None

def login_user(user_data):
    """Login and get access token"""
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    response = requests.post(f"{BACKEND_URL}/token", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        print(f"✅ User logged in successfully")
        return token_data["access_token"]
    else:
        print(f"❌ Failed to login: {response.status_code} - {response.text}")
        return None

def upload_test_file(token, csv_content):
    """Upload the test CSV file"""
    headers = {"Authorization": f"Bearer {token}"}
    
    files = {
        "file": ("test_reference_data.csv", csv_content, "text/csv")
    }
    
    response = requests.post(f"{BACKEND_URL}/upload", headers=headers, files=files)
    if response.status_code == 200:
        upload_data = response.json()
        print(f"✅ File uploaded successfully: {upload_data['file_id']}")
        return upload_data
    else:
        print(f"❌ Failed to upload file: {response.status_code} - {response.text}")
        return None

def test_preview_endpoint(token, file_id, column_mappings):
    """Test the preview endpoint with specific column mappings"""
    headers = {"Authorization": f"Bearer {token}"}
    
    data = {
        "file_id": file_id,
        "column_mappings": json.dumps(column_mappings),
        "preview_only": "true"
    }
    
    response = requests.post(f"{BACKEND_URL}/preview", headers=headers, data=data)
    if response.status_code == 200:
        preview_data = response.json()
        print(f"✅ Preview endpoint working successfully")
        return preview_data
    else:
        print(f"❌ Failed to get preview: {response.status_code} - {response.text}")
        return None

def analyze_preview_output(preview_data):
    """Analyze the preview output to verify Column D and E requirements"""
    print("\n" + "="*80)
    print("ANALYZING PREVIEW OUTPUT FOR COLUMN D (AMOUNT) AND COLUMN E (REFERENCE)")
    print("="*80)
    
    formatted_data = preview_data.get("formatted_data", [])
    
    if not formatted_data:
        print("❌ No formatted data found in preview response")
        return False
    
    print(f"\nTotal rows in preview: {len(formatted_data)}")
    print("\nColumn structure verification:")
    
    # Check if we have the expected columns
    if formatted_data:
        columns = list(formatted_data[0].keys())
        print(f"Columns found: {columns}")
        
        expected_columns = ["Date", "Cheque No.", "Description", "Amount", "Reference"]
        
        print(f"\nExpected Xero format columns:")
        print(f"Column A: Date -> {columns[0] if len(columns) > 0 else 'MISSING'}")
        print(f"Column B: Cheque No. -> {columns[1] if len(columns) > 1 else 'MISSING'}")
        print(f"Column C: Description -> {columns[2] if len(columns) > 2 else 'MISSING'}")
        print(f"Column D: Amount -> {columns[3] if len(columns) > 3 else 'MISSING'}")
        print(f"Column E: Reference -> {columns[4] if len(columns) > 4 else 'MISSING'}")
    
    print(f"\n{'Row':<3} | {'Original Ref':<12} | {'Column D (Amount)':<15} | {'Column E (Ref)':<12} | {'Expected':<20}")
    print("-" * 80)
    
    all_correct = True
    
    for i, row in enumerate(formatted_data):
        amount = row.get("Amount", "")
        reference = row.get("Reference", "")
        
        # Determine expected values based on test data
        test_references = ["Debit", "Credit", "D", "C", "DB", "CR", "Debit", "Credit"]
        test_amounts = ["150.00", "500.00", "1200.00", "75.00", "2500.00", "25.00", "300.00", "800.00"]
        
        if i < len(test_references):
            original_ref = test_references[i]
            original_amount = test_amounts[i]
            
            # Expected behavior:
            # Credits (C, CR, Credit) -> negative amount in Column D, "C" in Column E
            # Debits (D, DB, Debit) -> positive amount in Column D, "D" in Column E
            
            if original_ref.lower() in ['c', 'cr', 'credit']:
                expected_amount = f"-{original_amount}"
                expected_reference = "C"
            else:  # Debit cases
                expected_amount = original_amount
                expected_reference = "D"
            
            # Check if actual matches expected
            amount_correct = str(amount) == expected_amount
            reference_correct = str(reference) == expected_reference
            
            status = "✅" if (amount_correct and reference_correct) else "❌"
            
            print(f"{i+1:<3} | {original_ref:<12} | {amount:<15} | {reference:<12} | {expected_amount} / {expected_reference} {status}")
            
            if not (amount_correct and reference_correct):
                all_correct = False
                print(f"    ❌ Expected Amount: {expected_amount}, Got: {amount}")
                print(f"    ❌ Expected Reference: {expected_reference}, Got: {reference}")
    
    print("\n" + "="*80)
    if all_correct:
        print("✅ ALL TESTS PASSED: Column D and E formatting is working correctly!")
        print("✅ Credits show negative amounts in Column D and 'C' in Column E")
        print("✅ Debits show positive amounts in Column D and 'D' in Column E")
    else:
        print("❌ TESTS FAILED: Column D and E formatting has issues!")
    print("="*80)
    
    return all_correct

def main():
    """Main test function"""
    print("🧪 TESTING PREVIEW FUNCTIONALITY FOR COLUMN D (AMOUNT) AND COLUMN E (REFERENCE)")
    print("="*80)
    
    # Step 1: Create test CSV with Reference column
    print("\n1. Creating test CSV with Reference column...")
    csv_content = create_test_csv_with_reference()
    print("✅ Test CSV created with Credit/Debit reference values")
    
    # Step 2: Register and login user
    print("\n2. Setting up authentication...")
    user_data = register_test_user()
    if not user_data:
        return False
    
    token = login_user(user_data)
    if not token:
        return False
    
    # Step 3: Upload test file
    print("\n3. Uploading test file...")
    upload_data = upload_test_file(token, csv_content)
    if not upload_data:
        return False
    
    file_id = upload_data["file_id"]
    original_mapping = upload_data.get("column_mapping", {})
    
    print(f"Original auto-mapping: {original_mapping}")
    
    # Step 4: Test preview with Reference column mapping
    print("\n4. Testing preview endpoint with Reference column mapping...")
    
    # Create column mapping that includes transaction_type for Reference column
    column_mappings = {
        "A": "Date",           # Column A: Date
        "B": "Cheque No",      # Column B: Cheque No
        "C": "Description",    # Column C: Description  
        "D": "Amount",         # Column D: Amount
        "transaction_type": "Reference"  # Use Reference column for transaction type
    }
    
    print(f"Using column mappings: {column_mappings}")
    
    preview_data = test_preview_endpoint(token, file_id, column_mappings)
    if not preview_data:
        return False
    
    # Step 5: Analyze the preview output
    print("\n5. Analyzing preview output...")
    success = analyze_preview_output(preview_data)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 PREVIEW FUNCTIONALITY TEST COMPLETED SUCCESSFULLY!")
            exit(0)
        else:
            print("\n💥 PREVIEW FUNCTIONALITY TEST FAILED!")
            exit(1)
    except Exception as e:
        print(f"\n💥 TEST ERROR: {str(e)}")
        exit(1)