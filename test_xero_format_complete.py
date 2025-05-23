#!/usr/bin/env python3

import requests
import json
import csv
import io
from datetime import datetime

# Configuration
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com/api"

def create_comprehensive_test_csv():
    """Create a comprehensive test CSV file with various Reference formats"""
    test_data = [
        ["Date", "Description", "Amount", "Reference", "Cheque No"],
        ["01/01/2024", "Office Supplies Purchase", "150.00", "Debit", "CHQ001"],
        ["02/01/2024", "Sales Revenue", "500.00", "Credit", "CHQ002"],
        ["03/01/2024", "Rent Payment", "1200.00", "D", "CHQ003"],
        ["04/01/2024", "Customer Refund", "75.00", "C", "CHQ004"],
        ["05/01/2024", "Equipment Purchase", "2500.00", "DB", "CHQ005"],
        ["06/01/2024", "Interest Income", "25.00", "CR", "CHQ006"],
        ["07/01/2024", "Utility Bill Payment", "300.00", "Debit", "CHQ007"],
        ["08/01/2024", "Service Income", "800.00", "Credit", "CHQ008"],
        ["09/01/2024", "Bank Charges", "15.50", "Debit", "CHQ009"],
        ["10/01/2024", "Dividend Income", "120.75", "Credit", "CHQ010"]
    ]
    
    csv_content = io.StringIO()
    writer = csv.writer(csv_content)
    writer.writerows(test_data)
    csv_content.seek(0)
    
    return csv_content.getvalue()

def register_and_login():
    """Register and login a test user"""
    user_data = {
        "email": f"test_comprehensive_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
        "password": "testpassword123"
    }
    
    # Register
    response = requests.post(f"{BACKEND_URL}/register", json=user_data)
    if response.status_code != 200:
        print(f"❌ Failed to register user: {response.status_code} - {response.text}")
        return None
    
    # Login
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    response = requests.post(f"{BACKEND_URL}/token", data=login_data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        print(f"❌ Failed to login: {response.status_code} - {response.text}")
        return None

def test_complete_xero_format():
    """Test the complete Xero format structure and functionality"""
    print("🧪 COMPREHENSIVE XERO FORMAT TESTING")
    print("="*80)
    
    # Step 1: Authentication
    print("\n1. Setting up authentication...")
    token = register_and_login()
    if not token:
        return False
    print("✅ Authentication successful")
    
    # Step 2: Upload test file
    print("\n2. Uploading comprehensive test file...")
    csv_content = create_comprehensive_test_csv()
    
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("comprehensive_test.csv", csv_content, "text/csv")}
    
    response = requests.post(f"{BACKEND_URL}/upload", headers=headers, files=files)
    if response.status_code != 200:
        print(f"❌ Failed to upload file: {response.status_code} - {response.text}")
        return False
    
    upload_data = response.json()
    file_id = upload_data["file_id"]
    print(f"✅ File uploaded successfully: {file_id}")
    
    # Step 3: Test preview with proper column mapping
    print("\n3. Testing preview with Reference column mapping...")
    
    column_mappings = {
        "A": "Date",           # Column A: Contact/Description -> Date
        "B": "Cheque No",      # Column B: Date -> Cheque No
        "C": "Description",    # Column C: Description -> Description
        "D": "Amount",         # Column D: Amount (formatted with proper signs)
        "transaction_type": "Reference"  # Column E: Reference (D/C indicators)
    }
    
    data = {
        "file_id": file_id,
        "column_mappings": json.dumps(column_mappings),
        "preview_only": "true"
    }
    
    response = requests.post(f"{BACKEND_URL}/preview", headers=headers, data=data)
    if response.status_code != 200:
        print(f"❌ Failed to get preview: {response.status_code} - {response.text}")
        return False
    
    preview_data = response.json()
    print("✅ Preview generated successfully")
    
    # Step 4: Verify Xero format structure
    print("\n4. Verifying Xero format structure...")
    formatted_data = preview_data.get("formatted_data", [])
    
    if not formatted_data:
        print("❌ No formatted data found")
        return False
    
    # Check column structure
    columns = list(formatted_data[0].keys())
    expected_columns = ["Date", "Cheque No.", "Description", "Amount", "Reference"]
    
    print(f"\nColumn Structure Verification:")
    print(f"Expected: {expected_columns}")
    print(f"Actual:   {columns}")
    
    structure_correct = columns == expected_columns
    if structure_correct:
        print("✅ Column structure matches Xero format exactly")
    else:
        print("❌ Column structure does not match Xero format")
        return False
    
    # Step 5: Verify data formatting
    print(f"\n5. Verifying data formatting...")
    print(f"{'Row':<3} | {'Date':<12} | {'Cheque':<8} | {'Description':<25} | {'Amount':<10} | {'Ref':<3} | {'Status':<6}")
    print("-" * 85)
    
    all_correct = True
    test_references = ["Debit", "Credit", "D", "C", "DB", "CR", "Debit", "Credit", "Debit", "Credit"]
    
    for i, row in enumerate(formatted_data):
        date = row.get("Date", "")
        cheque = row.get("Cheque No.", "")
        description = row.get("Description", "")
        amount = row.get("Amount", "")
        reference = row.get("Reference", "")
        
        # Verify amount and reference logic
        if i < len(test_references):
            original_ref = test_references[i]
            
            # Check amount sign
            try:
                amount_value = float(amount)
                if original_ref.lower() in ['c', 'cr', 'credit']:
                    amount_correct = amount_value < 0
                    expected_ref = "C"
                else:
                    amount_correct = amount_value > 0
                    expected_ref = "D"
                
                reference_correct = str(reference) == expected_ref
                row_correct = amount_correct and reference_correct
                
                status = "✅" if row_correct else "❌"
                
                print(f"{i+1:<3} | {date:<12} | {cheque:<8} | {description[:25]:<25} | {amount:<10} | {reference:<3} | {status}")
                
                if not row_correct:
                    all_correct = False
                    if not amount_correct:
                        print(f"    ❌ Amount sign incorrect for {original_ref}")
                    if not reference_correct:
                        print(f"    ❌ Reference should be {expected_ref}, got {reference}")
                        
            except ValueError:
                print(f"{i+1:<3} | {date:<12} | {cheque:<8} | {description[:25]:<25} | {amount:<10} | {reference:<3} | ❌")
                print(f"    ❌ Amount is not a valid number: {amount}")
                all_correct = False
    
    # Step 6: Summary
    print(f"\n6. Test Summary:")
    print("="*80)
    
    if all_correct and structure_correct:
        print("✅ ALL TESTS PASSED!")
        print("✅ Column structure matches Xero format exactly:")
        print("   - Column A: Date")
        print("   - Column B: Cheque No.")
        print("   - Column C: Description")
        print("   - Column D: Amount (with proper +/- signs based on reference)")
        print("   - Column E: Reference (D for debits, C for credits)")
        print("✅ Amount formatting working correctly:")
        print("   - Credits show negative amounts and 'C' reference")
        print("   - Debits show positive amounts and 'D' reference")
        print("✅ Preview functionality is working as requested!")
        return True
    else:
        print("❌ TESTS FAILED!")
        if not structure_correct:
            print("❌ Column structure does not match Xero format")
        if not all_correct:
            print("❌ Data formatting has issues")
        return False

if __name__ == "__main__":
    try:
        success = test_complete_xero_format()
        if success:
            print("\n🎉 COMPREHENSIVE XERO FORMAT TEST COMPLETED SUCCESSFULLY!")
            exit(0)
        else:
            print("\n💥 COMPREHENSIVE XERO FORMAT TEST FAILED!")
            exit(1)
    except Exception as e:
        print(f"\n💥 TEST ERROR: {str(e)}")
        exit(1)