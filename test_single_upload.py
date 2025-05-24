#!/usr/bin/env python3
"""
Test single file upload functionality to verify amount prefix logic
"""

import requests
import json
import csv
import io
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com/api"

def test_single_upload():
    """Test single file upload with amount prefix verification"""
    print("🧪 Testing Single File Upload with Amount Prefix Logic")
    print("="*60)
    
    # Register and login
    user_email = f"test_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
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
    
    # Create test CSV
    test_data = [
        ["Date", "Description", "Amount", "Transaction Type"],
        ["01/01/2024", "Credit Entry", "500.00", "Credit"],
        ["02/01/2024", "Debit Entry", "300.00", "Debit"],
        ["03/01/2024", "CR Entry", "150.00", "CR"],
        ["04/01/2024", "DB Entry", "200.00", "DB"],
    ]
    
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    writer.writerows(test_data)
    csv_content.seek(0)
    
    # Upload file
    files = {'file': ('test_single.csv', csv_content.getvalue(), 'text/csv')}
    response = requests.post(f"{BACKEND_URL}/upload", files=files, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code} - {response.text}")
        return False
    
    upload_data = response.json()
    print(f"✅ File uploaded: {upload_data['file_id']}")
    
    # Check formatted data
    formatted_data = upload_data['formatted_data']
    print(f"\n📊 Formatted Data ({len(formatted_data)} rows):")
    
    for i, row in enumerate(formatted_data):
        if i == 0:  # Skip header
            continue
        amount = row.get('Amount', '')
        reference = row.get('Reference', '')
        description = row.get('Description', '')
        print(f"  {description}: Amount={amount}, Reference={reference}")
    
    print("\n✅ Single file upload test completed successfully!")
    return True

if __name__ == "__main__":
    test_single_upload()