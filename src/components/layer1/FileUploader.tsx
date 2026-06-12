"use client";

import React, { useState, useRef } from 'react';
import { Badge } from '../ui/Badge';

export const FileUploader: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setSuccess(false);

    const formData = new FormData();
    formData.append('file', file);

    try {
      // Hardcoded to the active namespace for the demo pipeline
      const runId = 'turing-active-run';
      const response = await fetch(`http://127.0.0.1:8000/runs/${runId}/layer1/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown upload error');
    } finally {
      setIsUploading(false);
      // Reset input so the user can upload another file if needed
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="w-full flex flex-col bg-white border-b-2 border-black p-6 relative">
      <div className="font-mono text-xs font-bold tracking-widest text-gray-500 mb-4 shrink-0">
        STEP 0: UPLOAD DATASET
      </div>
      
      <div className="relative group shrink-0">
        <input 
          type="file" 
          accept=".csv,.xlsx,.xls,.txt,.json,.pdf,.md"
          ref={fileInputRef}
          onChange={handleFileChange}
          disabled={isUploading}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10 disabled:cursor-not-allowed"
        />
        <div className={`w-full flex flex-col items-center justify-center border-2 border-dashed p-8 transition-colors duration-200
          ${isUploading ? 'border-orange-500 bg-orange-50' : 'border-gray-300 group-hover:border-black bg-[#F9FAFB] group-hover:bg-gray-100'}
        `}>
          <span className="font-mono text-sm font-semibold text-black tracking-widest mb-2">
            {isUploading ? 'UPLOADING...' : 'DRAG & DROP OR CLICK TO BROWSE'}
          </span>
          <span className="font-mono text-[10px] text-gray-500">
            ACCEPTED FORMATS: CSV, EXCEL, TXT, JSON, PDF, MD
          </span>
        </div>
      </div>

      {error && (
        <div className="mt-4 font-mono text-[10px] text-red-500 font-bold bg-red-50 p-2 border border-red-200">
          SYSTEM ERROR: {error}
        </div>
      )}

      {success && (
        <div className="mt-4 font-mono text-[10px] text-green-700 font-bold bg-green-50 p-2 border border-green-200 flex items-center justify-between animate-fade-in">
          <span>DATASET INGESTED. L1 CAUSAL DISCOVERY READY.</span>
          <Badge variant="success">✅</Badge>
        </div>
      )}
    </div>
  );
};
