import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

// Get backend URL from environment
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Authentication Context
const AuthContext = createContext();

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      fetchUserProfile(token);
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUserProfile = async (token) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${BACKEND_URL}/api/token`, 
        new URLSearchParams({
          'username': email,
          'password': password,
        }), {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          }
        }
      );
      
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      
      await fetchUserProfile(access_token);
      return true;
    } catch (error) {
      toast.error('Login failed: ' + (error.response?.data?.detail || 'Unknown error'));
      return false;
    }
  };

  const register = async (email, password) => {
    try {
      await axios.post(`${BACKEND_URL}/api/register`, { email, password });
      toast.success('Registration successful! Please login.');
      return true;
    } catch (error) {
      toast.error('Registration failed: ' + (error.response?.data?.detail || 'Unknown error'));
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

function useAuth() {
  return useContext(AuthContext);
}

// Protected Route Component
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  
  if (loading) {
    return <div className="flex items-center justify-center min-h-screen">
      <div className="loader"></div>
    </div>;
  }
  
  if (!user) {
    return <Navigate to="/login" />;
  }
  
  return children;
}

// File Upload Component
function FileUploader({ onFileProcessed }) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  
  const { getRootProps, getInputProps } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: false,
    onDrop: async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;
      
      setUploadError(null);
      const file = acceptedFiles[0];
      setIsUploading(true);
      
      try {
        const formData = new FormData();
        formData.append('file', file);
        
        const token = localStorage.getItem('token');
        const response = await axios.post(`${BACKEND_URL}/api/upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`
          }
        });
        
        onFileProcessed(response.data, file.name);
        toast.success('File uploaded successfully!');
      } catch (error) {
        const errorMessage = error.response?.data?.detail || 'Unknown error occurred';
        setUploadError(errorMessage);
        toast.error('Upload failed: ' + errorMessage);
        console.error('File upload error:', error);
      } finally {
        setIsUploading(false);
      }
    }
  });

  return (
    <div className="mt-6">
      <div {...getRootProps({ className: 'dropzone' })}>
        <input {...getInputProps()} />
        <div className="text-center p-10 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 transition duration-200">
          {isUploading ? (
            <div className="flex flex-col items-center">
              <div className="loader mb-4"></div>
              <p>Uploading and processing file...</p>
            </div>
          ) : (
            <>
              <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="mt-4 text-sm text-gray-600">
                <span className="font-medium text-indigo-600 hover:text-indigo-500">
                  Drag and drop your CSV or XLSX file here, or click to browse
                </span>
              </p>
              <p className="mt-1 text-xs text-gray-500">Files will be automatically mapped to Xero format</p>
              {uploadError && (
                <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                  <p className="font-semibold">Error uploading file:</p>
                  <p>{uploadError}</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Column Mapper Component
function ColumnMapper({ originalColumns, columnMapping, onMappingChange, onUpdatePreview, isUpdatingPreview }) {
  const targetColumns = [
    { id: 'A', name: 'Date (dd/mm/yyyy)' },
    { id: 'B', name: 'Cheque No.' },
    { id: 'C', name: 'Description' },
    { id: 'D', name: 'Amount' },
    { id: 'E', name: 'Reference' },
    { id: 'transaction_type', name: 'Transaction Type (optional)' }
  ];

  const handleMappingChange = (targetColumn, sourceColumn) => {
    const newMapping = { ...columnMapping, [targetColumn]: sourceColumn };
    onMappingChange(newMapping);
  };

  return (
    <div className="mt-6 bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Column Mapping</h3>
      <div className="space-y-4">
        {targetColumns.map((target) => (
          <div key={target.id} className="flex items-center">
            <div className="w-1/3 font-medium">{target.name}:</div>
            <div className="w-2/3">
              <select
                className="w-full p-2 border border-gray-300 rounded"
                value={columnMapping[target.id] || ''}
                onChange={(e) => handleMappingChange(target.id, e.target.value)}
              >
                <option value="">-- Select a column --</option>
                {originalColumns.map((column) => (
                  <option key={column} value={column}>
                    {column}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 text-sm text-gray-600">
        <p><strong>Note:</strong></p>
        <ul className="list-disc pl-5 space-y-1">
          <li>Date will be formatted as dd/mm/yyyy</li>
          <li>Amount: Debits will be prefixed with a negative sign</li>
          <li>Reference: Will add 'D' for debits and 'C' for credits</li>
        </ul>
      </div>
      <div className="mt-6 flex justify-end">
        <button
          onClick={onUpdatePreview}
          className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={isUpdatingPreview}
        >
          {isUpdatingPreview ? (
            <span className="flex items-center">
              <div className="loader-sm mr-2"></div>
              Updating...
            </span>
          ) : (
            'Update Preview'
          )}
        </button>
      </div>
    </div>
  );
}

// Data Table Component
function DataTable({ data, title }) {
  if (!data || data.length === 0) {
    return <div className="text-center p-4">No data to display</div>;
  }

  const columns = Object.keys(data[0]);

  return (
    <div className="overflow-x-auto rounded-lg shadow">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {data.map((row, rowIndex) => (
            <tr key={rowIndex} className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
              {columns.map((column) => (
                <td key={`${rowIndex}-${column}`} className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {row[column] !== null && row[column] !== undefined ? String(row[column]) : ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Dashboard Page
function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [conversions, setConversions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConversions();
  }, []);

  const fetchConversions = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/conversions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setConversions(response.data);
    } catch (error) {
      toast.error('Failed to fetch conversions');
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (conversionId) => {
    try {
      const token = localStorage.getItem('token');
      
      // Use axios to get the file as a blob
      const response = await axios.get(`${BACKEND_URL}/api/download/${conversionId}`, {
        responseType: 'blob',
        headers: { Authorization: `Bearer ${token}` }
      });
      
      // Create a URL for the blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      
      // Create a temporary link element
      const link = document.createElement('a');
      link.href = url;
      
      // Set the filename from the Content-Disposition header if available
      // or use a default name
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'xero_formatted.csv';
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
        if (filenameMatch && filenameMatch.length === 2) {
          filename = filenameMatch[1];
        }
      }
      link.setAttribute('download', filename);
      
      // Append the link to the body, click it, and remove it
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast.success('Download started!');
    } catch (error) {
      toast.error('Failed to download file: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Download error:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-indigo-600">Xero Converter</h1>
              </div>
            </div>
            <div className="flex items-center">
              <span className="text-gray-700 mr-4">Welcome, {user?.email}</span>
              <button
                onClick={logout}
                className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 rounded"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-semibold text-gray-800">Your Dashboard</h2>
            <button
              onClick={() => navigate('/convert')}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded"
            >
              New Conversion
            </button>
          </div>

          <div className="bg-white overflow-hidden shadow rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Conversion History</h3>
              
              {loading ? (
                <div className="flex justify-center py-4">
                  <div className="loader"></div>
                </div>
              ) : conversions.length === 0 ? (
                <div className="text-center py-4 text-gray-500">
                  No conversions yet. Start by creating a new conversion.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Original Filename
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Formatted Filename
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {conversions.map((conversion) => (
                        <tr key={conversion.id}>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {conversion.original_filename}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {conversion.formatted_filename}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                            {new Date(conversion.created_at).toLocaleString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => handleDownload(conversion.id)}
                              className="text-indigo-600 hover:text-indigo-900"
                            >
                              Download
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// File Conversion Page
function FileConversion() {
  const navigate = useNavigate();
  const [fileData, setFileData] = useState(null);
  const [originalFilename, setOriginalFilename] = useState('');
  const [columnMapping, setColumnMapping] = useState({});
  const [formattedData, setFormattedData] = useState([]);
  const [formattedFilename, setFormattedFilename] = useState('');
  const [isConverting, setIsConverting] = useState(false);
  const [isUpdatingPreview, setIsUpdatingPreview] = useState(false);

  const handleFileProcessed = (data, filename) => {
    setFileData(data);
    setOriginalFilename(filename);
    setColumnMapping(data.column_mapping);
    setFormattedData(data.formatted_data);
    setFormattedFilename(filename.replace(/\.[^/.]+$/, '') + '_formatted.csv');
  };

  const handleUpdatePreview = async () => {
    if (!fileData) return;
    
    setIsUpdatingPreview(true);
    
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file_id', fileData.file_id);
      formData.append('column_mappings', JSON.stringify(columnMapping));
      formData.append('preview_only', 'true');
      
      const response = await axios.post(`${BACKEND_URL}/api/preview`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      setFormattedData(response.data.formatted_data);
      toast.success('Preview updated with new column mapping!');
    } catch (error) {
      toast.error('Failed to update preview: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Preview update error:', error);
    } finally {
      setIsUpdatingPreview(false);
    }
  };

  const handleConvertFile = async () => {
    if (!fileData) return;
    
    setIsConverting(true);
    
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file_id', fileData.file_id);
      formData.append('column_mappings', JSON.stringify(columnMapping));
      formData.append('formatted_filename', formattedFilename);
      
      const response = await axios.post(`${BACKEND_URL}/api/convert`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      setFormattedData(response.data.formatted_data);
      toast.success('File converted successfully!');
      
      // Download the converted file
      try {
        const downloadResponse = await axios.get(`${BACKEND_URL}/api/download/${response.data.conversion_id}`, {
          responseType: 'blob',
          headers: { Authorization: `Bearer ${token}` }
        });
        
        // Create a URL for the blob
        const url = window.URL.createObjectURL(new Blob([downloadResponse.data]));
        
        // Create a temporary link element
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', formattedFilename || 'xero_formatted.csv');
        
        // Append the link to the body, click it, and remove it
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        toast.success('Download started!');
      } catch (downloadError) {
        toast.error('Download failed, but conversion was successful. You can download from the dashboard.');
        console.error('Download error:', downloadError);
      }
      
      // Navigate to dashboard after successful conversion
      setTimeout(() => {
        navigate('/');
      }, 2000);
    } catch (error) {
      toast.error('Conversion failed: ' + (error.response?.data?.detail || 'Unknown error'));
    } finally {
      setIsConverting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center">
                <h1 className="text-xl font-bold text-indigo-600">Xero Converter</h1>
              </div>
            </div>
            <div className="flex items-center">
              <Link to="/" className="text-indigo-600 hover:text-indigo-900 font-medium">
                Back to Dashboard
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div className="px-4 py-6 sm:px-0">
          <div className="bg-white shadow overflow-hidden sm:rounded-lg">
            <div className="px-4 py-5 sm:p-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Convert File to Xero Format</h2>
              
              {!fileData ? (
                <div>
                  <div className="bg-blue-50 p-4 rounded-lg mb-6">
                    <h3 className="text-md font-medium text-blue-800 mb-2">File Format Guidelines:</h3>
                    <ul className="list-disc pl-5 text-sm text-blue-700 space-y-1">
                      <li>Upload CSV or XLSX files containing financial transaction data</li>
                      <li>Ensure your file has columns for date, description, and amount</li>
                      <li>Files with headers will be automatically mapped to Xero format</li>
                      <li>Dates should be in a standard format (e.g., YYYY-MM-DD or MM/DD/YYYY)</li>
                      <li>Amount values should be numeric (positive for income, negative for expenses)</li>
                    </ul>
                  </div>
                  <FileUploader onFileProcessed={handleFileProcessed} />
                </div>
              ) : (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-medium">File: {originalFilename}</h3>
                    <button
                      onClick={() => setFileData(null)}
                      className="text-gray-600 hover:text-gray-900"
                    >
                      Upload a different file
                    </button>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div>
                      <h4 className="text-md font-medium mb-2">Original Data</h4>
                      <DataTable data={fileData.original_data} title="Original Data" />
                    </div>
                    <div>
                      <h4 className="text-md font-medium mb-2">Formatted Data (Preview)</h4>
                      <DataTable data={formattedData} title="Formatted Data" />
                    </div>
                  </div>
                  
                  <ColumnMapper
                    originalColumns={fileData.original_columns}
                    columnMapping={columnMapping}
                    onMappingChange={setColumnMapping}
                    onUpdatePreview={handleUpdatePreview}
                    isUpdatingPreview={isUpdatingPreview}
                  />
                  
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <label htmlFor="formatted-filename" className="block text-sm font-medium text-gray-700 mb-2">
                      Output Filename
                    </label>
                    <div className="flex">
                      <input
                        type="text"
                        id="formatted-filename"
                        value={formattedFilename}
                        onChange={(e) => setFormattedFilename(e.target.value)}
                        className="flex-1 p-2 border border-gray-300 rounded-l"
                        placeholder="filename_formatted.csv"
                      />
                      <span className="inline-flex items-center px-3 bg-gray-200 text-gray-600 text-sm border border-l-0 border-gray-300 rounded-r">
                        {!formattedFilename.endsWith('.csv') ? '.csv' : ''}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex justify-end">
                    <button
                      onClick={handleConvertFile}
                      disabled={isConverting}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-6 rounded disabled:opacity-50"
                    >
                      {isConverting ? (
                        <span className="flex items-center">
                          <div className="loader-sm mr-2"></div>
                          Converting...
                        </span>
                      ) : (
                        'Convert and Download'
                      )}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Login Page
function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    
    const success = await login(email, password);
    
    setIsLoading(false);
    if (success) {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Sign in to your account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email-address" className="sr-only">Email address</label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? (
                <span className="flex items-center">
                  <div className="loader-sm mr-2"></div>
                  Signing in...
                </span>
              ) : (
                'Sign in'
              )}
            </button>
          </div>
          
          <div className="text-center">
            <p className="text-sm text-gray-600">
              Don't have an account?{' '}
              <Link to="/register" className="font-medium text-indigo-600 hover:text-indigo-500">
                Register here
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

// Register Page
function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }
    
    setIsLoading(true);
    
    const success = await register(email, password);
    
    setIsLoading(false);
    if (success) {
      navigate('/login');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Create a new account
          </h2>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="rounded-md shadow-sm -space-y-px">
            <div>
              <label htmlFor="email-address" className="sr-only">Email address</label>
              <input
                id="email-address"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-t-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Email address"
              />
            </div>
            <div>
              <label htmlFor="password" className="sr-only">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Password"
              />
            </div>
            <div>
              <label htmlFor="confirm-password" className="sr-only">Confirm Password</label>
              <input
                id="confirm-password"
                name="confirm-password"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 focus:z-10 sm:text-sm"
                placeholder="Confirm Password"
              />
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? (
                <span className="flex items-center">
                  <div className="loader-sm mr-2"></div>
                  Registering...
                </span>
              ) : (
                'Register'
              )}
            </button>
          </div>
          
          <div className="text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-indigo-600 hover:text-indigo-500">
                Sign in
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

// Main App
function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          } />
          <Route path="/convert" element={
            <ProtectedRoute>
              <FileConversion />
            </ProtectedRoute>
          } />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <ToastContainer position="top-right" autoClose={3000} />
      </AuthProvider>
    </Router>
  );
}

export default App;
