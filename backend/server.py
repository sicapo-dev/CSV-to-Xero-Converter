import os
import pandas as pd
import numpy as np
import uuid
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from pymongo import MongoClient
import re
import io
import json
from bson.json_util import dumps
from openpyxl import load_workbook

# Set up MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "xero_converter")
client = MongoClient(MONGO_URL)
db = client[DB_NAME]

# Set up FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up JWT authentication
SECRET_KEY = os.environ.get("SECRET_KEY", "a_very_secret_key_for_development_only")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# Set up password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# Models
class User(BaseModel):
    id: Optional[str] = None
    email: EmailStr
    password: Optional[str] = None
    created_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class UserInDB(User):
    hashed_password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class Folder(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    parent_folder_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileRecord(BaseModel):
    id: Optional[str] = None
    user_id: str
    folder_id: Optional[str] = None
    original_filename: str
    file_type: str  # "csv" or "xlsx"
    size_bytes: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class FileConversion(BaseModel):
    id: Optional[str] = None
    user_id: str
    file_id: str
    original_filename: str
    formatted_filename: str
    column_mapping: Dict[str, str]
    created_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ColumnMapping(BaseModel):
    source_column: str
    target_column: str

class ConversionRequest(BaseModel):
    column_mappings: List[ColumnMapping]
    formatted_filename: Optional[str] = None

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(email):
    user_data = db.users.find_one({"email": email})
    if user_data:
        # Convert MongoDB document to dict and add empty password field
        user_dict = dict(user_data)
        # Ensure ObjectId is converted to string
        if '_id' in user_dict:
            user_dict['_id'] = str(user_dict['_id'])
        return UserInDB(**user_dict)
    return None

def authenticate_user(email, password):
    user = get_user(email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = get_user(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user

# Routes for authentication
@app.post("/api/register", response_model=UserResponse)
async def register(user_create: UserCreate):
    if get_user(user_create.email):
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    hashed_password = get_password_hash(user_create.password)
    user_id = str(uuid.uuid4())
    user_data = {
        "id": user_id,
        "email": user_create.email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    
    db.users.insert_one(user_data)
    
    return {
        "id": user_id,
        "email": user_create.email,
        "created_at": user_data["created_at"]
    }

@app.post("/api/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at
    }

# File parsing helper functions
def parse_file_content(file_content, file_type):
    if file_type == "csv":
        # Parse CSV with pandas
        df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))
    elif file_type == "xlsx":
        # Parse XLSX with pandas
        df = pd.read_excel(io.BytesIO(file_content))
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Replace NaN, Infinity, and -Infinity with None to avoid JSON serialization issues
    df = df.replace([float('inf'), -float('inf'), float('nan')], None)
    
    return df

def format_date(date_str):
    try:
        # Try to parse the date using pandas
        date = pd.to_datetime(date_str)
        return date.strftime('%d/%m/%Y')
    except:
        # Return the original string if parsing fails
        return date_str

def format_amount(amount_str, reference_str=None):
    """
    Format amount for Xero based on reference value:
    - If reference contains "C", "CR", or "Credit" -> Add minus prefix (Credit = negative in Xero)
    - If reference contains "D", "DB", or "Debit" -> Leave as positive (Debit = positive in Xero)
    - If no reference provided, keep original behavior
    """
    # Convert to string if not already
    amount_str = str(amount_str) if amount_str is not None else ""
    
    # Remove all punctuation except for the decimal point
    cleaned_amount = re.sub(r'[^\d.-]', '', amount_str)
    
    try:
        # Convert to float
        amount = float(cleaned_amount)
        
        # Check reference if provided
        if reference_str is not None and isinstance(reference_str, str):
            reference_lower = reference_str.lower()
            
            # Reference indicates Credit -> add minus prefix (Credit = negative in Xero)
            if any(term in reference_lower for term in ['c', 'cr', 'credit']):
                if amount > 0:  # Only add minus if positive
                    return f"-{cleaned_amount}"
                return cleaned_amount  # Already negative
            
            # Reference indicates Debit -> leave as positive (Debit = positive in Xero)
            elif any(term in reference_lower for term in ['d', 'db', 'debit']):
                if amount < 0:  # Remove minus if negative
                    return cleaned_amount.replace('-', '')
                return cleaned_amount  # Already positive
        
        # Default behavior (no reference or unrecognized reference)
        # Keep as is
        return cleaned_amount
    except:
        return amount_str

def add_reference_code(amount_str, transaction_type=None):
    """
    Determine if a transaction is a debit or credit based on:
    1. The transaction type column if provided (db/dr/debit = D, cr/credit = C)
    2. The amount value (negative = D, positive = C) if transaction type not provided or not recognized
    """
    # First check if there's a transaction type provided
    if transaction_type is not None and isinstance(transaction_type, str):
        transaction_type = transaction_type.lower().strip()
        
        # Check for debit indicators
        if transaction_type in ['db', 'dr', 'debit', 'dbt', 'debited', 'd']:
            return "D"
        
        # Check for credit indicators
        if transaction_type in ['cr', 'credit', 'cdt', 'credited', 'c']:
            return "C"
    
    # Fall back to amount-based detection if transaction type not recognized
    try:
        amount = float(str(amount_str).replace(',', ''))
        return "D" if amount < 0 else "C"
    except:
        return ""

def auto_map_columns(df):
    """Auto-map columns to Xero format based on content analysis"""
    column_mapping = {}
    columns = df.columns.tolist()
    
    # Look for date column
    date_candidates = [col for col in columns if any(term in col.lower() for term in ['date', 'dt', 'day'])]
    if date_candidates:
        column_mapping['A'] = date_candidates[0]
    else:
        # Try to find a column with date-like values
        for col in columns:
            if df[col].dtype == 'object':
                sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                if sample and isinstance(sample, str) and re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', sample):
                    column_mapping['A'] = col
                    break
    
    # Look for cheque/reference number
    cheque_candidates = [col for col in columns if any(term in col.lower() for term in ['cheque', 'check', 'ref', 'reference', 'no', 'num', 'number', 'id'])]
    if cheque_candidates:
        column_mapping['B'] = cheque_candidates[0]
    
    # Look for description
    desc_candidates = [col for col in columns if any(term in col.lower() for term in ['desc', 'narration', 'details', 'memo', 'note', 'particular', 'narr', 'transaction', 'name'])]
    if desc_candidates:
        column_mapping['C'] = desc_candidates[0]
    
    # Look for amount
    amount_candidates = [col for col in columns if any(term in col.lower() for term in ['amount', 'sum', 'value', 'debit', 'credit', 'amt'])]
    if amount_candidates:
        column_mapping['D'] = amount_candidates[0]
    
    # Look for transaction type column (for reference field)
    type_candidates = [col for col in columns if any(term in col.lower() for term in ['type', 'transaction type', 'tr type', 'db/cr', 'dr/cr', 'debit/credit'])]
    if type_candidates:
        column_mapping['transaction_type'] = type_candidates[0]
    
    # If we couldn't find specific columns, make best guesses
    if 'A' not in column_mapping and len(columns) > 0:
        column_mapping['A'] = columns[0]  # First column often contains dates
    
    if 'B' not in column_mapping and len(columns) > 1:
        column_mapping['B'] = columns[1]
    
    if 'C' not in column_mapping and len(columns) > 2:
        column_mapping['C'] = columns[2]
    
    if 'D' not in column_mapping and len(columns) > 3:
        # Look for numeric columns for amount
        numeric_cols = [col for col in columns if pd.api.types.is_numeric_dtype(df[col])]
        if numeric_cols:
            column_mapping['D'] = numeric_cols[0]
        else:
            column_mapping['D'] = columns[3] if len(columns) > 3 else ""
    
    # For reference, we'll derive it from the amount and transaction type if available
    if 'D' in column_mapping:
        column_mapping['E'] = column_mapping['D']  # Reference will be derived from amount and transaction type
    
    return column_mapping

def apply_xero_format(df, column_mapping):
    """Apply Xero formatting rules to the data"""
    xero_df = pd.DataFrame()
    
    # Check if we're using a transaction type column
    has_transaction_type = 'transaction_type' in column_mapping and column_mapping['transaction_type']
    
    # Format date (Column A)
    if 'A' in column_mapping and column_mapping['A']:
        xero_df['Date'] = df[column_mapping['A']].apply(format_date)
    else:
        xero_df['Date'] = ""
    
    # Add Cheque No. (Column B)
    if 'B' in column_mapping and column_mapping['B']:
        xero_df['Cheque No.'] = df[column_mapping['B']]
    else:
        xero_df['Cheque No.'] = ""
    
    # Add Description (Column C)
    if 'C' in column_mapping and column_mapping['C']:
        xero_df['Description'] = df[column_mapping['C']]
    else:
        xero_df['Description'] = ""
    
    # Format Amount (Column D)
    if 'D' in column_mapping and column_mapping['D']:
        # If we have a transaction type column, use it for reference-based formatting
        if has_transaction_type:
            xero_df['Amount'] = df.apply(
                lambda row: format_amount(
                    row[column_mapping['D']], 
                    row[column_mapping['transaction_type']] if pd.notna(row[column_mapping['transaction_type']]) else None
                ), 
                axis=1
            )
        else:
            # No reference column, use default formatting
            xero_df['Amount'] = df[column_mapping['D']].apply(lambda x: format_amount(x, None))
    else:
        xero_df['Amount'] = ""
    
    # Add Reference (Column E) - derived from Amount and Transaction Type if available
    if 'D' in column_mapping and column_mapping['D']:
        if has_transaction_type:
            # We have both amount and transaction type
            xero_df['Reference'] = df.apply(
                lambda row: add_reference_code(
                    row[column_mapping['D']], 
                    row[column_mapping['transaction_type']] if pd.notna(row[column_mapping['transaction_type']]) else None
                ), 
                axis=1
            )
        else:
            # We only have amount
            xero_df['Reference'] = df[column_mapping['D']].apply(add_reference_code)
    else:
        xero_df['Reference'] = ""
    
    return xero_df

# Routes for file conversion
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check folder if provided
        if folder_id and folder_id != "root":
            folder = db.folders.find_one({"id": folder_id, "user_id": current_user.id})
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")
        
        # Check file extension
        filename = file.filename.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx')):
            raise HTTPException(status_code=400, detail="Only CSV and XLSX files are supported")
        
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        file_type = "csv" if filename.endswith('.csv') else "xlsx"
        
        # Parse file
        df = parse_file_content(file_content, file_type)
        
        # Auto-map columns
        column_mapping = auto_map_columns(df)
        
        # Get column names for frontend display
        original_columns = df.columns.tolist()
        
        # Apply Xero format using the auto-mapping
        xero_df = apply_xero_format(df, column_mapping)
        
        # Handle problematic values for JSON serialization
        def safe_json_serialize(df):
            # Replace problematic values
            df_cleaned = df.copy()
            # Replace inf/-inf with None
            df_cleaned = df_cleaned.replace([np.inf, -np.inf], None)
            # Convert to records
            records = df_cleaned.to_dict(orient="records")
            # Convert all NaN to None for JSON serialization
            for record in records:
                for k, v in record.items():
                    if isinstance(v, float) and np.isnan(v):
                        record[k] = None
            return records
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        
        # Store file metadata in database
        file_record = {
            "id": file_id,
            "user_id": current_user.id,
            "folder_id": folder_id if folder_id else None,
            "original_filename": filename,
            "file_type": file_type,
            "size_bytes": file_size,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.files.insert_one(file_record)
        
        # Prepare response
        response = {
            "file_id": file_id,
            "original_filename": filename,
            "file_type": file_type,
            "size_bytes": file_size,
            "folder_id": folder_id,
            "created_at": file_record["created_at"].isoformat(),
            "original_data": safe_json_serialize(df.head(50)),
            "formatted_data": safe_json_serialize(xero_df.head(50)),
            "original_columns": original_columns,
            "column_mapping": column_mapping
        }
        
        # Store the dataframe for later use
        # Clean the dataframe before storing
        clean_df = df.replace([np.inf, -np.inf], None)
        records = clean_df.to_dict(orient="records")
        for record in records:
            for k, v in record.items():
                if isinstance(v, float) and np.isnan(v):
                    record[k] = None
        
        with open(f"/tmp/{file_id}_original.json", "w") as f:
            json.dump(records, f)
        
        return response
    
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/bulk-upload")
async def bulk_upload(
    files: List[UploadFile] = File(...),
    folder_id: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check folder if provided
        if folder_id and folder_id != "root":
            folder = db.folders.find_one({"id": folder_id, "user_id": current_user.id})
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")
        
        results = []
        
        for file in files:
            # Check file extension
            filename = file.filename.lower()
            if not (filename.endswith('.csv') or filename.endswith('.xlsx')):
                # Skip unsupported files but continue with others
                results.append({
                    "filename": filename,
                    "success": False,
                    "error": "Unsupported file type. Only CSV and XLSX files are supported."
                })
                continue
            
            try:
                # Read file content
                file_content = await file.read()
                file_size = len(file_content)
                file_type = "csv" if filename.endswith('.csv') else "xlsx"
                
                # Parse file
                df = parse_file_content(file_content, file_type)
                
                # Auto-map columns
                column_mapping = auto_map_columns(df)
                
                # Generate a unique file ID
                file_id = str(uuid.uuid4())
                
                # Store file metadata in database
                file_record = {
                    "id": file_id,
                    "user_id": current_user.id,
                    "folder_id": folder_id if folder_id else None,
                    "original_filename": filename,
                    "file_type": file_type,
                    "size_bytes": file_size,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                db.files.insert_one(file_record)
                
                # Store the dataframe for later use
                clean_df = df.replace([np.inf, -np.inf], None)
                records = clean_df.to_dict(orient="records")
                for record in records:
                    for k, v in record.items():
                        if isinstance(v, float) and np.isnan(v):
                            record[k] = None
                
                with open(f"/tmp/{file_id}_original.json", "w") as f:
                    json.dump(records, f)
                
                results.append({
                    "file_id": file_id,
                    "filename": filename,
                    "success": True
                })
            
            except Exception as e:
                results.append({
                    "filename": filename,
                    "success": False,
                    "error": str(e)
                })
        
        return {"results": results}
    
    except Exception as e:
        print(f"Error in bulk_upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/preview")
async def preview_conversion(
    file_id: str = Form(...),
    column_mappings: str = Form(...),
    preview_only: str = Form("false"),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check if file exists and belongs to the user
        file_record = db.files.find_one({"id": file_id, "user_id": current_user.id})
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Load the original data
        with open(f"/tmp/{file_id}_original.json", "r") as f:
            records = json.load(f)
            df = pd.DataFrame.from_records(records)
        
        # Parse column mappings
        column_mapping = json.loads(column_mappings)
        
        # Apply Xero format using the provided mapping
        xero_df = apply_xero_format(df, column_mapping)
        
        # Handle problematic values for JSON serialization
        def safe_json_serialize(df):
            # Replace problematic values
            df_cleaned = df.copy()
            # Replace inf/-inf with None
            df_cleaned = df_cleaned.replace([np.inf, -np.inf], None)
            # Convert to records
            records = df_cleaned.to_dict(orient="records")
            # Convert all NaN to None for JSON serialization
            for record in records:
                for k, v in record.items():
                    if isinstance(v, float) and np.isnan(v):
                        record[k] = None
            return records
        
        # Return the formatted data for preview
        return {
            "file_id": file_id,
            "formatted_data": safe_json_serialize(xero_df),
            "column_mapping": column_mapping,
            "message": "Preview updated with transaction type detection"
        }
    
    except Exception as e:
        print(f"Error in preview_conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/convert")
async def convert_file(
    file_id: str = Form(...),
    column_mappings: str = Form(...),
    formatted_filename: str = Form(None),
    current_user: User = Depends(get_current_user)
):
    try:
        # Check if file exists and belongs to the user
        file_record = db.files.find_one({"id": file_id, "user_id": current_user.id})
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Load the original data
        with open(f"/tmp/{file_id}_original.json", "r") as f:
            records = json.load(f)
            df = pd.DataFrame.from_records(records)
        
        # Parse column mappings
        column_mapping = json.loads(column_mappings)
        
        # Apply Xero format using the provided mapping
        xero_df = apply_xero_format(df, column_mapping)
        
        # Generate output filename
        if not formatted_filename:
            original_filename = file_record["original_filename"]
            formatted_filename = f"{original_filename.split('.')[0]}_formatted.csv"
        elif not formatted_filename.endswith('.csv'):
            formatted_filename += '.csv'
        
        # Save the formatted file
        output_path = f"/tmp/{file_id}_{formatted_filename}"
        xero_df.to_csv(output_path, index=False)
        
        # Store conversion record in database
        conversion = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "file_id": file_id,
            "original_filename": file_record["original_filename"],
            "formatted_filename": formatted_filename,
            "column_mapping": column_mapping,
            "created_at": datetime.utcnow()
        }
        db.conversions.insert_one(conversion)
        
        # Handle problematic values for JSON serialization
        def safe_json_serialize(df):
            # Replace problematic values
            df_cleaned = df.copy()
            # Replace inf/-inf with None
            df_cleaned = df_cleaned.replace([np.inf, -np.inf], None)
            # Convert to records
            records = df_cleaned.to_dict(orient="records")
            # Convert all NaN to None for JSON serialization
            for record in records:
                for k, v in record.items():
                    if isinstance(v, float) and np.isnan(v):
                        record[k] = None
            return records
        
        # Return the formatted data and download link
        return {
            "conversion_id": conversion["id"],
            "file_id": file_id,
            "formatted_filename": formatted_filename,
            "formatted_data": safe_json_serialize(xero_df)
        }
    
    except Exception as e:
        print(f"Error in convert_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversions")
async def get_conversions(current_user: User = Depends(get_current_user)):
    try:
        # Get all conversions for the current user
        conversions = list(db.conversions.find({"user_id": current_user.id}).sort("created_at", -1))
        
        # Parse the MongoDB BSON to JSON
        return json.loads(dumps(conversions))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download/{conversion_id}")
async def download_conversion(conversion_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Get conversion record
        conversion = db.conversions.find_one({"id": conversion_id, "user_id": current_user.id})
        if not conversion:
            raise HTTPException(status_code=404, detail="Conversion not found")
        
        # Get file path
        file_id = conversion.get("file_id")
        file_path = f"/tmp/{file_id}_{conversion['formatted_filename']}"
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # Return file content as a response
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path, 
            filename=conversion['formatted_filename'],
            media_type="text/csv"
        )
    
    except Exception as e:
        print(f"Error in download_conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Folder Management endpoints
@app.get("/api/folders")
async def get_folders(current_user: User = Depends(get_current_user)):
    try:
        # Get all folders for the current user
        folders = list(db.folders.find({"user_id": current_user.id}).sort("name", 1))
        
        # Convert ObjectId to string for each folder
        for folder in folders:
            if "_id" in folder:
                folder["_id"] = str(folder["_id"])
        
        return folders
    
    except Exception as e:
        print(f"Error in get_folders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/folders")
async def create_folder(name: str = Form(...), parent_folder_id: Optional[str] = Form(None), current_user: User = Depends(get_current_user)):
    try:
        # Validate parent folder if provided
        if parent_folder_id:
            parent_folder = db.folders.find_one({"id": parent_folder_id, "user_id": current_user.id})
            if not parent_folder:
                raise HTTPException(status_code=404, detail="Parent folder not found")
        
        # Create new folder
        folder = {
            "id": str(uuid.uuid4()),
            "user_id": current_user.id,
            "name": name,
            "parent_folder_id": parent_folder_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        db.folders.insert_one(folder)
        
        return folder
    
    except Exception as e:
        print(f"Error in create_folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/folders/{folder_id}")
async def update_folder(folder_id: str, name: str = Form(...), current_user: User = Depends(get_current_user)):
    try:
        # Check if folder exists and belongs to the user
        folder = db.folders.find_one({"id": folder_id, "user_id": current_user.id})
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        # Update folder
        db.folders.update_one(
            {"id": folder_id},
            {"$set": {"name": name, "updated_at": datetime.utcnow()}}
        )
        
        # Get updated folder
        updated_folder = db.folders.find_one({"id": folder_id})
        
        return json.loads(dumps(updated_folder))
    
    except Exception as e:
        print(f"Error in update_folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/folders/{folder_id}")
async def delete_folder(folder_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Check if folder exists and belongs to the user
        folder = db.folders.find_one({"id": folder_id, "user_id": current_user.id})
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        
        # Check if folder has files
        files = db.files.find({"folder_id": folder_id})
        if files.count() > 0:
            raise HTTPException(status_code=400, detail="Cannot delete folder with files. Please move or delete files first.")
        
        # Check if folder has subfolders
        subfolders = db.folders.find({"parent_folder_id": folder_id})
        if subfolders.count() > 0:
            raise HTTPException(status_code=400, detail="Cannot delete folder with subfolders. Please delete subfolders first.")
        
        # Delete folder
        db.folders.delete_one({"id": folder_id})
        
        return {"message": "Folder deleted successfully"}
    
    except Exception as e:
        print(f"Error in delete_folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# File Management endpoints
@app.get("/api/folders/{folder_id}/files")
async def get_files_in_folder(folder_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Check if folder exists and belongs to the user
        if folder_id != "root":
            folder = db.folders.find_one({"id": folder_id, "user_id": current_user.id})
            if not folder:
                raise HTTPException(status_code=404, detail="Folder not found")
            
            # Get all files in the folder
            files = list(db.files.find({"folder_id": folder_id, "user_id": current_user.id}).sort("created_at", -1))
        else:
            # Root folder - get files with no folder_id or null folder_id
            files = list(db.files.find({
                "$and": [
                    {"user_id": current_user.id},
                    {"$or": [
                        {"folder_id": None},
                        {"folder_id": "root"}
                    ]}
                ]
            }).sort("created_at", -1))
        
        # Get conversions for each file
        for file in files:
            # Convert ObjectId to string for file
            if "_id" in file:
                file["_id"] = str(file["_id"])
            
            conversions = list(db.conversions.find({"file_id": file["id"]}).sort("created_at", -1))
            # Convert ObjectId to string for conversions
            for conversion in conversions:
                if "_id" in conversion:
                    conversion["_id"] = str(conversion["_id"])
            file["conversions"] = conversions
        
        return files
    
    except Exception as e:
        print(f"Error in get_files_in_folder: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/files/move")
async def move_file(file_id: str = Form(...), target_folder_id: Optional[str] = Form(None), current_user: User = Depends(get_current_user)):
    try:
        # Check if file exists and belongs to the user
        file = db.files.find_one({"id": file_id, "user_id": current_user.id})
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Check if target folder exists if not root
        if target_folder_id and target_folder_id != "root":
            target_folder = db.folders.find_one({"id": target_folder_id, "user_id": current_user.id})
            if not target_folder:
                raise HTTPException(status_code=404, detail="Target folder not found")
        
        # Update file folder
        db.files.update_one(
            {"id": file_id},
            {"$set": {"folder_id": target_folder_id if target_folder_id else None, "updated_at": datetime.utcnow()}}
        )
        
        return {"message": "File moved successfully"}
    
    except Exception as e:
        print(f"Error in move_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Check if file exists and belongs to the user
        file = db.files.find_one({"id": file_id, "user_id": current_user.id})
        if not file:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Delete any associated conversions
        db.conversions.delete_many({"file_id": file_id})
        
        # Delete the file from database
        db.files.delete_one({"id": file_id})
        
        # Delete file from disk if it exists
        original_file_path = f"/tmp/{file_id}_original.json"
        if os.path.exists(original_file_path):
            os.remove(original_file_path)
        
        return {"message": "File deleted successfully"}
    
    except Exception as e:
        print(f"Error in delete_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files/{file_id}")
async def get_file(file_id: str, current_user: User = Depends(get_current_user)):
    try:
        # Check if file exists and belongs to the user
        file_record = db.files.find_one({"id": file_id, "user_id": current_user.id})
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Load the original data
        with open(f"/tmp/{file_id}_original.json", "r") as f:
            records = json.load(f)
            df = pd.DataFrame.from_records(records)
        
        # Auto-map columns
        column_mapping = auto_map_columns(df)
        
        # Apply Xero format using the auto-mapping
        xero_df = apply_xero_format(df, column_mapping)
        
        # Handle problematic values for JSON serialization
        def safe_json_serialize(df):
            # Replace problematic values
            df_cleaned = df.copy()
            # Replace inf/-inf with None
            df_cleaned = df_cleaned.replace([np.inf, -np.inf], None)
            # Convert to records
            records = df_cleaned.to_dict(orient="records")
            # Convert all NaN to None for JSON serialization
            for record in records:
                for k, v in record.items():
                    if isinstance(v, float) and np.isnan(v):
                        record[k] = None
            return records
        
        # Get column names for frontend display
        original_columns = df.columns.tolist()
        
        # Prepare response
        response = {
            "file_id": file_id,
            "original_filename": file_record["original_filename"],
            "file_type": file_record["file_type"],
            "size_bytes": file_record["size_bytes"],
            "folder_id": file_record.get("folder_id"),
            "created_at": file_record["created_at"].isoformat() if "created_at" in file_record else None,
            "original_data": safe_json_serialize(df.head(50)),
            "formatted_data": safe_json_serialize(xero_df.head(50)),
            "original_columns": original_columns,
            "column_mapping": column_mapping
        }
        
        return response
    
    except Exception as e:
        print(f"Error in get_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Status endpoint
@app.get("/api/status")
async def get_status():
    return {"status": "OK", "version": "1.0.0"}
