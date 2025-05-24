#!/usr/bin/env python3
"""
Comprehensive test for the corrected amount prefix logic.

User Requirements:
- If Reference contains C, CR, or Credit → Amount remains POSITIVE (no prefix)
- If Reference contains D, DB, or Debit → Prefix Amount with "-" to make it NEGATIVE

This test verifies:
1. Credit Scenarios: Reference values "C", "CR", "Credit" should result in POSITIVE amounts
2. Debit Scenarios: Reference values "D", "DB", "Debit" should result in NEGATIVE amounts
3. Mixed Case Testing: Test "credit", "DEBIT", "Cr", etc.
4. Verification: Create test data and verify the preview endpoint shows:
   - Credits: positive amounts in Column D, "C" in Column E
   - Debits: negative amounts in Column D, "D" in Column E
"""

import requests
import json
import csv
import io
import os
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com/api"

class AmountPrefixTester:
    def __init__(self):
        self.token = None
        self.user_email = f"test_amount_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        self.user_password = "testpassword123"
        
    def register_and_login(self):
        """Register a test user and get authentication token"""
        print("🔐 Registering test user...")
        
        # Register user
        register_data = {
            "email": self.user_email,
            "password": self.user_password
        }
        
        response = requests.post(f"{BACKEND_URL}/register", json=register_data)
        if response.status_code != 200:
            print(f"❌ Registration failed: {response.status_code} - {response.text}")
            return False
            
        print(f"✅ User registered: {self.user_email}")
        
        # Login to get token
        login_data = {
            "username": self.user_email,
            "password": self.user_password
        }
        
        response = requests.post(f"{BACKEND_URL}/token", data=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
            
        token_data = response.json()
        self.token = token_data["access_token"]
        print("✅ Authentication successful")
        return True
    
    def create_test_csv(self):
        """Create comprehensive test CSV with various reference formats"""
        test_data = [
            # Header row
            ["Date", "Description", "Amount", "Reference"],
            
            # Credit scenarios - should result in POSITIVE amounts
            ["01/01/2024", "Credit Transaction 1", "500.00", "C"],
            ["02/01/2024", "Credit Transaction 2", "75.50", "CR"],
            ["03/01/2024", "Credit Transaction 3", "1200.00", "Credit"],
            ["04/01/2024", "Credit Transaction 4", "250.75", "credit"],  # lowercase
            ["05/01/2024", "Credit Transaction 5", "100.00", "CREDIT"],  # uppercase
            ["06/01/2024", "Credit Transaction 6", "300.25", "Cr"],      # mixed case
            
            # Debit scenarios - should result in NEGATIVE amounts
            ["07/01/2024", "Debit Transaction 1", "150.00", "D"],
            ["08/01/2024", "Debit Transaction 2", "85.25", "DB"],
            ["09/01/2024", "Debit Transaction 3", "400.00", "Debit"],
            ["10/01/2024", "Debit Transaction 4", "200.50", "debit"],    # lowercase
            ["11/01/2024", "Debit Transaction 5", "350.00", "DEBIT"],    # uppercase
            ["12/01/2024", "Debit Transaction 6", "125.75", "Db"],       # mixed case
            
            # Edge cases
            ["13/01/2024", "Mixed Case Test 1", "50.00", "cR"],         # mixed case credit
            ["14/01/2024", "Mixed Case Test 2", "60.00", "dB"],         # mixed case debit
            ["15/01/2024", "Unknown Reference", "70.00", "Unknown"],    # unknown reference
        ]
        
        # Create CSV content
        csv_content = io.StringIO()
        writer = csv.writer(csv_content)
        writer.writerows(test_data)
        csv_content.seek(0)
        
        return csv_content.getvalue()
    
    def upload_test_file(self):
        """Upload the test CSV file"""
        print("📤 Uploading test CSV file...")
        
        csv_content = self.create_test_csv()
        
        files = {
            'file': ('test_amount_prefix.csv', csv_content, 'text/csv')
        }
        
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        
        response = requests.post(f"{BACKEND_URL}/upload", files=files, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ File upload failed: {response.status_code} - {response.text}")
            return None
            
        upload_data = response.json()
        print(f"✅ File uploaded successfully: {upload_data['file_id']}")
        return upload_data
    
    def test_preview_functionality(self, file_id, column_mapping):
        """Test the preview endpoint with specific column mapping"""
        print("🔍 Testing preview functionality...")
        
        headers = {
            'Authorization': f'Bearer {self.token}'
        }
        
        # Test preview with transaction_type mapping
        preview_data = {
            'file_id': file_id,
            'column_mappings': json.dumps(column_mapping),
            'preview_only': 'true'
        }
        
        response = requests.post(f"{BACKEND_URL}/preview", data=preview_data, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Preview failed: {response.status_code} - {response.text}")
            return None
            
        preview_result = response.json()
        print("✅ Preview generated successfully")
        return preview_result
    
    def verify_amount_logic(self, formatted_data):
        """Verify that the amount prefix logic is working correctly"""
        print("🧪 Verifying amount prefix logic...")
        
        results = {
            'credits_correct': 0,
            'credits_total': 0,
            'debits_correct': 0,
            'debits_total': 0,
            'errors': []
        }
        
        for i, row in enumerate(formatted_data):
            description = row.get('Description', '')
            amount = row.get('Amount', '')
            reference = row.get('Reference', '')
            
            print(f"Row {i+1}: {description} | Amount: {amount} | Reference: {reference}")
            
            # Skip header or empty rows
            if not description or 'Transaction' not in description:
                continue
                
            # Determine expected behavior based on description
            if 'Credit' in description:
                results['credits_total'] += 1
                # Credits should be POSITIVE amounts with "C" reference
                try:
                    amount_value = float(str(amount).replace(',', ''))
                    if amount_value > 0 and reference == 'C':
                        results['credits_correct'] += 1
                        print(f"  ✅ Credit correctly formatted: +{amount_value} with reference 'C'")
                    else:
                        error_msg = f"Credit incorrectly formatted: amount={amount_value}, reference='{reference}' (expected positive amount with 'C')"
                        results['errors'].append(error_msg)
                        print(f"  ❌ {error_msg}")
                except ValueError:
                    error_msg = f"Credit amount parsing failed: '{amount}'"
                    results['errors'].append(error_msg)
                    print(f"  ❌ {error_msg}")
                    
            elif 'Debit' in description:
                results['debits_total'] += 1
                # Debits should be NEGATIVE amounts with "D" reference
                try:
                    amount_value = float(str(amount).replace(',', ''))
                    if amount_value < 0 and reference == 'D':
                        results['debits_correct'] += 1
                        print(f"  ✅ Debit correctly formatted: {amount_value} with reference 'D'")
                    else:
                        error_msg = f"Debit incorrectly formatted: amount={amount_value}, reference='{reference}' (expected negative amount with 'D')"
                        results['errors'].append(error_msg)
                        print(f"  ❌ {error_msg}")
                except ValueError:
                    error_msg = f"Debit amount parsing failed: '{amount}'"
                    results['errors'].append(error_msg)
                    print(f"  ❌ {error_msg}")
        
        return results
    
    def print_test_summary(self, results):
        """Print comprehensive test summary"""
        print("\n" + "="*60)
        print("📊 AMOUNT PREFIX LOGIC TEST SUMMARY")
        print("="*60)
        
        print(f"\n🟢 CREDITS:")
        print(f"   Correct: {results['credits_correct']}/{results['credits_total']}")
        if results['credits_total'] > 0:
            credit_percentage = (results['credits_correct'] / results['credits_total']) * 100
            print(f"   Success Rate: {credit_percentage:.1f}%")
        
        print(f"\n🔴 DEBITS:")
        print(f"   Correct: {results['debits_correct']}/{results['debits_total']}")
        if results['debits_total'] > 0:
            debit_percentage = (results['debits_correct'] / results['debits_total']) * 100
            print(f"   Success Rate: {debit_percentage:.1f}%")
        
        total_correct = results['credits_correct'] + results['debits_correct']
        total_tests = results['credits_total'] + results['debits_total']
        
        print(f"\n📈 OVERALL:")
        print(f"   Total Correct: {total_correct}/{total_tests}")
        if total_tests > 0:
            overall_percentage = (total_correct / total_tests) * 100
            print(f"   Overall Success Rate: {overall_percentage:.1f}%")
        
        if results['errors']:
            print(f"\n❌ ERRORS FOUND ({len(results['errors'])}):")
            for i, error in enumerate(results['errors'], 1):
                print(f"   {i}. {error}")
        else:
            print(f"\n✅ NO ERRORS FOUND!")
        
        # Final verdict
        print(f"\n🎯 VERDICT:")
        if total_correct == total_tests and total_tests > 0:
            print("   ✅ AMOUNT PREFIX LOGIC IS WORKING CORRECTLY!")
        else:
            print("   ❌ AMOUNT PREFIX LOGIC HAS ISSUES!")
        
        print("="*60)
    
    def run_comprehensive_test(self):
        """Run the complete test suite"""
        print("🚀 Starting Comprehensive Amount Prefix Logic Test")
        print("="*60)
        
        # Step 1: Authentication
        if not self.register_and_login():
            return False
        
        # Step 2: Upload test file
        upload_data = self.upload_test_file()
        if not upload_data:
            return False
        
        file_id = upload_data['file_id']
        original_mapping = upload_data['column_mapping']
        
        print(f"\n📋 Original auto-mapping: {original_mapping}")
        
        # Step 3: Test with transaction_type mapping for reference-based formatting
        # We need to map the Reference column as transaction_type for proper processing
        test_mapping = {
            'A': 'Date',           # Date column
            'B': '',               # No cheque number in our test data
            'C': 'Description',    # Description column
            'D': 'Amount',         # Amount column
            'transaction_type': 'Reference'  # Reference column for transaction type
        }
        
        print(f"\n🔧 Test mapping with transaction_type: {test_mapping}")
        
        # Step 4: Test preview functionality
        preview_data = self.test_preview_functionality(file_id, test_mapping)
        if not preview_data:
            return False
        
        formatted_data = preview_data['formatted_data']
        
        print(f"\n📊 Preview data received ({len(formatted_data)} rows)")
        
        # Step 5: Verify amount logic
        results = self.verify_amount_logic(formatted_data)
        
        # Step 6: Print summary
        self.print_test_summary(results)
        
        return results

def main():
    """Main test execution"""
    tester = AmountPrefixTester()
    
    try:
        results = tester.run_comprehensive_test()
        
        if results:
            # Return appropriate exit code
            total_correct = results['credits_correct'] + results['debits_correct']
            total_tests = results['credits_total'] + results['debits_total']
            
            if total_correct == total_tests and total_tests > 0:
                print("\n🎉 All tests passed!")
                return 0
            else:
                print(f"\n⚠️  {total_tests - total_correct} tests failed!")
                return 1
        else:
            print("\n💥 Test execution failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test execution error: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())