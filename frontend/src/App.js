import React, { useState, useEffect, createContext, useContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';

// Get backend URL from environment
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

// Logo Component
function Logo({ className = "" }) {
  return (
    <div className={`flex flex-col items-center ${className}`}>
      <div className="text-4xl font-bold">CSV</div>
      <div className="my-2">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M19 13L12 20L5 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M12 4V20" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <div className="text-4xl font-bold">Xero</div>
    </div>
  );
}

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
function FileUploader({ onFileProcessed, folderId }) {
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
        
        // Add folder ID if provided
        if (folderId) {
          formData.append('folder_id', folderId);
        }
        
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
          <li>Amount: When no Transaction Type is provided, debits will be prefixed with a negative sign</li>
          <li>Amount: When Transaction Type is provided, original amount signs will be preserved</li>
          <li>Reference: Will add 'D' for debits and 'C' for credits based on Transaction Type or amount sign</li>
          <li>Transaction Type: If provided, values like 'DB', 'DR', 'CR' will determine debit/credit status</li>
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
  const [folders, setFolders] = useState([]);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFolderId, setSelectedFolderId] = useState('root');
  const [selectedFileId, setSelectedFileId] = useState(null);
  const [showCreateFolderModal, setShowCreateFolderModal] = useState(false);
  const [showMoveFileModal, setShowMoveFileModal] = useState(false);
  const [fileToMove, setFileToMove] = useState(null);
  const [showBulkUploader, setShowBulkUploader] = useState(false);

  useEffect(() => {
    fetchFolders();
  }, []);

  useEffect(() => {
    if (selectedFolderId) {
      fetchFiles(selectedFolderId);
    }
  }, [selectedFolderId]);

  const fetchFolders = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/folders`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFolders(response.data);
    } catch (error) {
      toast.error('Failed to fetch folders');
      console.error('Error fetching folders:', error);
    }
  };

  const fetchFiles = async (folderId) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/folders/${folderId}/files`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setFiles(response.data);
    } catch (error) {
      toast.error('Failed to fetch files');
      console.error('Error fetching files:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateFolder = async (name, parentFolderId = null) => {
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('name', name);
      if (parentFolderId) {
        formData.append('parent_folder_id', parentFolderId);
      }
      
      await axios.post(`${BACKEND_URL}/api/folders`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      toast.success('Folder created successfully');
      fetchFolders();
    } catch (error) {
      toast.error('Failed to create folder: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Error creating folder:', error);
    }
  };

  const handleRenameFolder = async (folderId, newName) => {
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('name', newName);
      
      await axios.put(`${BACKEND_URL}/api/folders/${folderId}`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      toast.success('Folder renamed successfully');
      fetchFolders();
    } catch (error) {
      toast.error('Failed to rename folder: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Error renaming folder:', error);
    }
  };

  const handleDeleteFolder = async (folderId) => {
    if (!window.confirm('Are you sure you want to delete this folder?')) {
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${BACKEND_URL}/api/folders/${folderId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('Folder deleted successfully');
      fetchFolders();
      
      // If the deleted folder was selected, go back to root
      if (selectedFolderId === folderId) {
        setSelectedFolderId('root');
      }
    } catch (error) {
      toast.error('Failed to delete folder: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Error deleting folder:', error);
    }
  };

  const handleDeleteFile = async (fileId) => {
    if (!window.confirm('Are you sure you want to delete this file? All associated conversions will also be deleted.')) {
      return;
    }
    
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${BACKEND_URL}/api/files/${fileId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      toast.success('File deleted successfully');
      fetchFiles(selectedFolderId);
      
      if (selectedFileId === fileId) {
        setSelectedFileId(null);
      }
    } catch (error) {
      toast.error('Failed to delete file: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Error deleting file:', error);
    }
  };

  const handleMoveFile = (fileId) => {
    setFileToMove(fileId);
    setShowMoveFileModal(true);
  };

  const handleMoveFileSubmit = async (fileId, targetFolderId) => {
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file_id', fileId);
      formData.append('target_folder_id', targetFolderId);
      
      await axios.post(`${BACKEND_URL}/api/files/move`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${token}`
        }
      });
      
      toast.success('File moved successfully');
      fetchFiles(selectedFolderId);
    } catch (error) {
      toast.error('Failed to move file: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Error moving file:', error);
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

  const handleSelectFile = (fileId) => {
    setSelectedFileId(fileId === selectedFileId ? null : fileId);
  };

  const handleFilesProcessed = (results) => {
    // Refresh files list after processing
    fetchFiles(selectedFolderId);
    setShowBulkUploader(false);
  };

  const handleSingleFileUpload = () => {
    navigate('/convert', { state: { folderId: selectedFolderId } });
  };

  // Find the selected file
  const selectedFile = files.find(file => file.id === selectedFileId);

  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <Logo className="h-10 text-indigo-600 scale-75" />
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
            <h2 className="text-2xl font-semibold text-gray-800">Your Files</h2>
            <div className="flex space-x-2">
              <button
                onClick={() => setShowCreateFolderModal(true)}
                className="bg-white hover:bg-gray-100 text-gray-800 font-semibold py-2 px-4 border border-gray-300 rounded shadow-sm"
              >
                <span className="flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" clipRule="evenodd" />
                    <path d="M10 9a1 1 0 011 1v2h2a1 1 0 110 2h-2v2a1 1 0 11-2 0v-2H7a1 1 0 110-2h2v-2a1 1 0 011-1z" />
                  </svg>
                  New Folder
                </span>
              </button>
              <button
                onClick={handleSingleFileUpload}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded shadow-sm"
              >
                <span className="flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                  </svg>
                  Upload File
                </span>
              </button>
              <button
                onClick={() => setShowBulkUploader(!showBulkUploader)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded shadow-sm"
              >
                <span className="flex items-center">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M5.5 13a3.5 3.5 0 01-.369-6.98 4 4 0 117.753-1.977A4.5 4.5 0 1113.5 13H11V9.413l1.293 1.293a1 1 0 001.414-1.414l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13H5.5z" />
                    <path d="M9 13h2v5a1 1 0 11-2 0v-5z" />
                  </svg>
                  Bulk Upload
                </span>
              </button>
            </div>
          </div>

          {showBulkUploader && (
            <div className="mb-6">
              <BulkUploader onFilesProcessed={handleFilesProcessed} folderId={selectedFolderId} />
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Folder navigation panel */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-medium">Folders</h3>
              </div>
              <div className="p-4 space-y-2">
                <div 
                  className={`flex items-center p-2 rounded-md cursor-pointer ${selectedFolderId === 'root' ? 'bg-indigo-100' : 'hover:bg-gray-100'}`}
                  onClick={() => setSelectedFolderId('root')}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
                  </svg>
                  <span className="flex-1 text-sm">Root</span>
                </div>
                
                {folders.map(folder => (
                  <Folder 
                    key={folder.id}
                    folder={folder}
                    selected={selectedFolderId === folder.id}
                    onSelect={setSelectedFolderId}
                    onRename={handleRenameFolder}
                    onDelete={handleDeleteFolder}
                  />
                ))}
              </div>
            </div>
            
            {/* Files panel */}
            <div className="lg:col-span-3 bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-medium">
                  Files in {selectedFolderId === 'root' ? 'Root' : folders.find(f => f.id === selectedFolderId)?.name || ''}
                </h3>
              </div>
              <div className="p-4">
                {loading ? (
                  <div className="flex justify-center py-8">
                    <div className="loader"></div>
                  </div>
                ) : files.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No files in this folder. Upload some files to get started.
                  </div>
                ) : (
                  <div className="space-y-2">
                    {files.map(file => (
                      <FileItem 
                        key={file.id}
                        file={file}
                        selected={selectedFileId === file.id}
                        onSelect={handleSelectFile}
                        onDelete={handleDeleteFile}
                        onMove={handleMoveFile}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          {/* Selected file details */}
          {selectedFile && (
            <div className="mt-6 bg-white rounded-lg shadow overflow-hidden">
              <div className="p-4 border-b border-gray-200">
                <h3 className="text-lg font-medium">File Details: {selectedFile.original_filename}</h3>
              </div>
              <div className="p-4">
                {selectedFile.conversions && selectedFile.conversions.length > 0 ? (
                  <div>
                    <h4 className="text-md font-medium mb-2">Conversions</h4>
                    <div className="overflow-x-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                          <tr>
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
                          {selectedFile.conversions.map((conversion) => (
                            <tr key={conversion.id}>
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
                  </div>
                ) : (
                  <div className="text-center py-4 text-gray-500">
                    No conversions yet. Convert this file to Xero format to see it here.
                  </div>
                )}
                
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={() => navigate('/convert', { state: { fileId: selectedFile.id } })}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2 px-4 rounded"
                  >
                    Convert to Xero Format
                  </button>
                </div>
              </div>
            </div>
          )}
          
          {/* Modals */}
          <CreateFolderModal
            isOpen={showCreateFolderModal}
            onClose={() => setShowCreateFolderModal(false)}
            onCreateFolder={handleCreateFolder}
            parentFolderId={selectedFolderId !== 'root' ? selectedFolderId : null}
          />
          
          <MoveFileModal
            isOpen={showMoveFileModal}
            onClose={() => setShowMoveFileModal(false)}
            onMoveFile={handleMoveFileSubmit}
            fileId={fileToMove}
            folders={folders}
            currentFolderId={selectedFolderId}
          />
        </div>
      </div>
    </div>
  );
}

// File Conversion Page
function FileConversion() {
  const navigate = useNavigate();
  const location = window.location.search ? window.location.search : null;
  const params = new URLSearchParams(location);
  const fileIdFromUrl = params.get('fileId');
  const folderIdFromUrl = params.get('folderId');
  
  const [fileData, setFileData] = useState(null);
  const [originalFilename, setOriginalFilename] = useState('');
  const [columnMapping, setColumnMapping] = useState({});
  const [formattedData, setFormattedData] = useState([]);
  const [formattedFilename, setFormattedFilename] = useState('');
  const [isConverting, setIsConverting] = useState(false);
  const [isUpdatingPreview, setIsUpdatingPreview] = useState(false);
  const [fileId, setFileId] = useState(fileIdFromUrl || null);
  const [folderId, setFolderId] = useState(folderIdFromUrl || 'root');
  const [isLoading, setIsLoading] = useState(!!fileIdFromUrl);

  useEffect(() => {
    if (fileId) {
      fetchFileData(fileId);
    }
  }, [fileId]);

  const fetchFileData = async (id) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${BACKEND_URL}/api/files/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.data && response.data.original_data) {
        setFileData(response.data);
        setOriginalFilename(response.data.original_filename);
        setColumnMapping(response.data.column_mapping || {});
        setFormattedData(response.data.formatted_data || []);
        setFormattedFilename(response.data.original_filename.replace(/\.[^/.]+$/, '') + '_formatted.csv');
      }
    } catch (error) {
      toast.error('Failed to fetch file data: ' + (error.response?.data?.detail || 'Unknown error'));
      console.error('Error fetching file data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileProcessed = (data, filename) => {
    setFileId(data.file_id);
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
      formData.append('file_id', fileId);
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
      formData.append('file_id', fileId);
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
            <div className="flex items-center">
              <div className="flex-shrink-0 flex items-center">
                <Logo className="h-10 text-indigo-600 scale-75" />
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
              
              {isLoading ? (
                <div className="flex justify-center py-12">
                  <div className="loader"></div>
                </div>
              ) : !fileData ? (
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
                      onClick={() => {
                        setFileData(null);
                        setFileId(null);
                      }}
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
          <Logo className="mx-auto text-indigo-600" />
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
          <Logo className="mx-auto text-indigo-600" />
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

// Folder Component
function Folder({ folder, onSelect, onRename, onDelete, selected }) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [newName, setNewName] = useState(folder.name);
  
  const handleRename = (e) => {
    e.stopPropagation();
    if (isRenaming) {
      onRename(folder.id, newName);
      setIsRenaming(false);
    } else {
      setIsRenaming(true);
    }
  };
  
  const handleDelete = (e) => {
    e.stopPropagation();
    onDelete(folder.id);
  };
  
  return (
    <div 
      className={`flex items-center p-2 rounded-md cursor-pointer ${selected ? 'bg-indigo-100' : 'hover:bg-gray-100'}`}
      onClick={() => onSelect(folder.id)}
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M2 6a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1H8a3 3 0 00-3 3v1.5a1.5 1.5 0 01-3 0V6z" clipRule="evenodd" />
        <path d="M6 12a2 2 0 012-2h8a2 2 0 012 2v2a2 2 0 01-2 2H8a2 2 0 01-2-2v-2z" />
      </svg>
      
      {isRenaming ? (
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              onRename(folder.id, newName);
              setIsRenaming(false);
            } else if (e.key === 'Escape') {
              setNewName(folder.name);
              setIsRenaming(false);
            }
          }}
          onClick={(e) => e.stopPropagation()}
          autoFocus
          className="border rounded px-2 py-1 text-sm flex-1 mr-2"
        />
      ) : (
        <span className="flex-1 text-sm">{folder.name}</span>
      )}
      
      <div className="flex space-x-1">
        <button
          onClick={handleRename}
          className="text-gray-500 hover:text-indigo-700 p-1 rounded"
          title={isRenaming ? "Save" : "Rename"}
        >
          {isRenaming ? (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
              <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
            </svg>
          )}
        </button>
        <button
          onClick={handleDelete}
          className="text-gray-500 hover:text-red-700 p-1 rounded"
          title="Delete"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// File Item Component
function FileItem({ file, onSelect, onDelete, onMove, selected }) {
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    else if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    else return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };
  
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };
  
  return (
    <div 
      className={`flex items-center p-2 rounded-md cursor-pointer ${selected ? 'bg-indigo-100' : 'hover:bg-gray-100'}`}
      onClick={() => onSelect(file.id)}
    >
      <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-indigo-500 mr-2" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
      </svg>
      
      <div className="flex-1">
        <div className="text-sm font-medium">{file.original_filename}</div>
        <div className="text-xs text-gray-500">
          {formatFileSize(file.size_bytes)} • Uploaded: {formatDate(file.created_at)}
        </div>
      </div>
      
      <div className="flex space-x-1">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onMove(file.id);
          }}
          className="text-gray-500 hover:text-indigo-700 p-1 rounded"
          title="Move"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
          </svg>
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(file.id);
          }}
          className="text-gray-500 hover:text-red-700 p-1 rounded"
          title="Delete"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// Create Folder Modal
function CreateFolderModal({ isOpen, onClose, onCreateFolder, parentFolderId }) {
  const [folderName, setFolderName] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (folderName.trim()) {
      onCreateFolder(folderName, parentFolderId);
      setFolderName('');
      onClose();
    }
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-medium mb-4">Create New Folder</h3>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="folder-name" className="block text-sm font-medium text-gray-700 mb-1">
              Folder Name
            </label>
            <input
              type="text"
              id="folder-name"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded"
              autoFocus
            />
          </div>
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 border border-transparent rounded shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Move File Modal
function MoveFileModal({ isOpen, onClose, onMoveFile, fileId, folders, currentFolderId }) {
  const [selectedFolderId, setSelectedFolderId] = useState(currentFolderId || 'root');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    onMoveFile(fileId, selectedFolderId);
    onClose();
  };
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-medium mb-4">Move File</h3>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="target-folder" className="block text-sm font-medium text-gray-700 mb-1">
              Select Destination Folder
            </label>
            <select
              id="target-folder"
              value={selectedFolderId}
              onChange={(e) => setSelectedFolderId(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded"
            >
              <option value="root">Root Folder</option>
              {folders.map((folder) => (
                <option key={folder.id} value={folder.id}>
                  {folder.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-gray-300 rounded shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 border border-transparent rounded shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700"
            >
              Move
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Bulk Upload Component
function BulkUploader({ onFilesProcessed, folderId }) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  
  const { getRootProps, getInputProps } = useDropzone({
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    multiple: true,
    onDrop: async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;
      
      setUploadError(null);
      setIsUploading(true);
      
      try {
        const formData = new FormData();
        acceptedFiles.forEach(file => {
          formData.append('files', file);
        });
        
        if (folderId) {
          formData.append('folder_id', folderId);
        }
        
        const token = localStorage.getItem('token');
        const response = await axios.post(`${BACKEND_URL}/api/bulk-upload`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
            'Authorization': `Bearer ${token}`
          }
        });
        
        onFilesProcessed(response.data.results);
        
        // Count successful uploads
        const successCount = response.data.results.filter(r => r.success).length;
        toast.success(`${successCount} of ${acceptedFiles.length} files uploaded successfully!`);
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
    <div className="mt-4">
      <div {...getRootProps({ className: 'dropzone' })}>
        <input {...getInputProps()} />
        <div className="text-center p-6 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 hover:bg-gray-100 transition duration-200">
          {isUploading ? (
            <div className="flex flex-col items-center">
              <div className="loader mb-4"></div>
              <p>Uploading and processing files...</p>
            </div>
          ) : (
            <>
              <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48" aria-hidden="true">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <p className="mt-4 text-sm text-gray-600">
                <span className="font-medium text-indigo-600 hover:text-indigo-500">
                  Drag and drop multiple CSV or XLSX files here, or click to browse
                </span>
              </p>
              <p className="mt-1 text-xs text-gray-500">Upload up to 20 files at once (10MB max per file)</p>
              {uploadError && (
                <div className="mt-2 text-sm text-red-600 bg-red-50 p-2 rounded">
                  <p className="font-semibold">Error uploading files:</p>
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
