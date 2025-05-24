#!/usr/bin/env python3
"""
Test the complete conversion workflow including download functionality
"""

import requests
import json
import csv
import io
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com/api"

def test_conversion_workflow():
    """Test complete conversion workflow"""
    print("🔄 Testing Complete Conversion Workflow")
    print("="*60)
    
    # Register and login
    user_email = f"test_convert_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    user_password = "testpassword123"
    
    # Register
    register_data = {"email": user_email, "password": user_password}
    response = requests.post(f"{BACKEND_URL}/register", json=register_data)
    if response.status_code != 200:
        print(f"❌ Registration failed: {response.status_code}")
        return False
    
    # Login
    login_data = {"username": user_email, "password": user_password}
    response = requests.post(f"{BACKEND_URL}/token", data=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
    
    token = response.json()["access_token"]
    headers = {'Authorization': f'Bearer {token}'}
    
    # Create test CSV with mixed reference formats
    test_data = [
        ["Date", "Description", "Amount", "Reference"],
        ["01/01/2024", "Credit Payment", "1000.00", "Credit"],
        ["02/01/2024", "Debit Charge", "500.00", "Debit"],
        ["03/01/2024", "CR Transaction", "250.00", "CR"],
        ["04/01/2024", "DB Transaction", "150.00", "DB"],
        ["05/01/2024", "C Entry", "75.00", "C"],
        ["06/01/2024", "D Entry", "100.00", "D"],
    ]
    
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    writer.writerows(test_data)
    csv_content.seek(0)
    
    # Upload file
    files = {'file': ('test_conversion.csv', csv_content.getvalue(), 'text/csv')}
    response = requests.post(f"{BACKEND_URL}/upload", files=files, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        return False
    
    upload_data = response.json()
    file_id = upload_data['file_id']
    print(f"✅ File uploaded: {file_id}")
    
    # Set up column mapping for conversion
    column_mapping = {
        'A': 'Date',
        'B': '',  # No cheque number
        'C': 'Description',
        'D': 'Amount',
        'transaction_type': 'Reference'  # Map Reference column for transaction type
    }
    
    # Convert file
    convert_data = {
        'file_id': file_id,
        'column_mappings': json.dumps(column_mapping),
        'formatted_filename': 'test_conversion_output.csv'
    }
    
    response = requests.post(f"{BACKEND_URL}/convert", data=convert_data, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Conversion failed: {response.status_code} - {response.text}")
        return False
    
    conversion_data = response.json()
    conversion_id = conversion_data['conversion_id']
    print(f"✅ File converted: {conversion_id}")
    
    # Verify formatted data
    formatted_data = conversion_data['formatted_data']
    print(f"\n📊 Conversion Results:")
    print("Description | Amount | Reference | Expected")
    print("-" * 50)
    
    expected_results = [
        ("Credit Payment", "1000.0", "C", "✅ Credit → Positive"),
        ("Debit Charge", "-500.0", "D", "✅ Debit → Negative"),
        ("CR Transaction", "250.0", "C", "✅ CR → Positive"),
        ("DB Transaction", "-150.0", "D", "✅ DB → Negative"),
        ("C Entry", "75.0", "C", "✅ C → Positive"),
        ("D Entry", "-100.0", "D", "✅ D → Negative"),
    ]
    
    all_correct = True
    for i, row in enumerate(formatted_data):
        if i < len(expected_results):
            expected_desc, expected_amount, expected_ref, note = expected_results[i]
            actual_desc = row.get('Description', '')
            actual_amount = str(row.get('Amount', ''))
            actual_ref = row.get('Reference', '')
            
            if actual_desc == expected_desc and actual_amount == expected_amount and actual_ref == expected_ref:
                print(f"{actual_desc} | {actual_amount} | {actual_ref} | {note}")
            else:
                print(f"{actual_desc} | {actual_amount} | {actual_ref} | ❌ MISMATCH")
                all_correct = False
    
    # Test download functionality
    print(f"\n📥 Testing download functionality...")
    response = requests.get(f"{BACKEND_URL}/download/{conversion_id}", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Download failed: {response.status_code}")
        return False
    
    # Check if we got CSV content
    if 'text/csv' in response.headers.get('content-type', ''):
        print("✅ Download successful - CSV file received")
        
        # Parse and verify downloaded content
        csv_content = response.text
        lines = csv_content.strip().split('\n')
        print(f"✅ Downloaded file has {len(lines)} lines (including header)")
        
        # Show first few lines
        print("\n📄 Downloaded CSV content (first 3 lines):")
        for i, line in enumerate(lines[:3]):
            print(f"  {i+1}: {line}")
    else:
        print(f"❌ Download returned unexpected content type: {response.headers.get('content-type')}")
        all_correct = False
    
    # Test conversion history
    print(f"\n📚 Testing conversion history...")
    response = requests.get(f"{BACKEND_URL}/conversions", headers=headers)
    
    if response.status_code != 200:
        print(f"❌ History retrieval failed: {response.status_code}")
        return False
    
    conversions = response.json()
    print(f"✅ Retrieved {len(conversions)} conversion(s) from history")
    
    if conversions:
        latest = conversions[0]
        print(f"   Latest: {latest.get('original_filename')} → {latest.get('formatted_filename')}")
    
    print(f"\n🎯 FINAL RESULT:")
    if all_correct:
        print("✅ ALL TESTS PASSED - Amount prefix logic working correctly!")
        return True
    else:
        print("❌ SOME TESTS FAILED - Issues found with amount prefix logic!")
        return False

if __name__ == "__main__":
    success = test_conversion_workflow()
    exit(0 if success else 1)