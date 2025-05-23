import requests
import json
import pandas as pd
from io import StringIO
import uuid

# Test the amount prefix logic specifically
BACKEND_URL = "https://073c2ac2-806b-4513-b576-7f4117f1530b.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

# Use existing token from previous test
auth_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0XzMyMjZjODExLTcxNDEtNDY0Yy1hZGQ5LWViMmJhNDFhN2YwOEBleGFtcGxlLmNvbSIsImV4cCI6MTc0ODEyODMzOX0.HQJFZCvMZWevQ3us5HXrHBv8tzfJGRxjnDYwtEnnCj0"

def create_simple_reference_test():
    """Create a simple CSV to test reference-based amount formatting"""
    data = {
        'Date': ['01/01/2023', '02/01/2023'],
        'Reference': ['C', 'D'],
        'Description': ['Credit Transaction', 'Debit Transaction'],
        'Amount': [100.00, 200.00]
    }
    df = pd.DataFrame(data)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

def test_reference_logic():
    headers = {"Authorization": f"Bearer {auth_token}"}
    
    # Upload test file
    csv_data = create_simple_reference_test()
    files = {'file': ('simple_ref_test.csv', csv_data, 'text/csv')}
    
    response = requests.post(f"{API_URL}/upload", headers=headers, files=files)
    print(f"Upload response: {response.status_code}")
    if response.status_code != 200:
        print(f"Upload failed: {response.text}")
        return
    
    file_data = response.json()
    file_id = file_data["file_id"]
    print(f"Original data: {file_data.get('original_data', [])}")
    print(f"Column mapping: {file_data.get('column_mapping', {})}")
    
    # Test conversion with explicit Reference column mapping
    column_mapping = {
        "A": "Date",
        "B": "Reference",  # This should be used for amount formatting
        "C": "Description",
        "D": "Amount",
        "E": "Amount"
    }
    
    data = {
        'file_id': file_id,
        'column_mappings': json.dumps(column_mapping),
        'formatted_filename': f"debug_test_{uuid.uuid4()}.csv"
    }
    
    response = requests.post(f"{API_URL}/convert", headers=headers, data=data)
    print(f"Convert response: {response.status_code}")
    if response.status_code != 200:
        print(f"Convert failed: {response.text}")
        return
    
    result = response.json()
    formatted_data = result.get("formatted_data", [])
    print(f"Formatted data: {formatted_data}")
    
    # Check if amounts are correctly formatted
    for i, row in enumerate(formatted_data):
        print(f"Row {i+1}: {row}")

if __name__ == "__main__":
    test_reference_logic()