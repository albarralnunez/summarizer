import { useState, useRef } from 'react';
import { SummaryResponse } from '../types';

export const useFileUpload = () => {
  const [result, setResult] = useState<SummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [responseTime, setResponseTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showToast, setShowToast] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const xhrRef = useRef<XMLHttpRequest | null>(null);
  const uploadStartTimeRef = useRef<number | null>(null);
  const uploadEndTimeRef = useRef<number | null>(null);

  const handleSubmit = async (formData: FormData) => {
    setIsLoading(true);
    setError(null);
    setShowToast(false);
    setUploadProgress(0);
    setResult(null);
    setResponseTime(null);
    uploadStartTimeRef.current = Date.now();

    return new Promise<void>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhrRef.current = xhr;

      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(progress);
        }
      });

      xhr.upload.addEventListener('loadend', () => {
        uploadEndTimeRef.current = Date.now();
      });

      xhr.addEventListener('load', async () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data: SummaryResponse = JSON.parse(xhr.responseText);
            const uploadTime = (uploadEndTimeRef.current! - uploadStartTimeRef.current!) / 1000;
            const processingTime = (Date.now() - uploadEndTimeRef.current!) / 1000;
            const totalTime = uploadTime + processingTime;
            
            setResult(data);
            setResponseTime(totalTime);
            resolve();
          } catch (err) {
            setError('Failed to parse response');
            setShowToast(true);
            reject(err);
          }
        } else {
          try {
            const errorData = JSON.parse(xhr.responseText);
            setError(errorData.detail || 'Failed to summarize file');
          } catch {
            setError('Failed to summarize file');
          }
          setShowToast(true);
          reject(new Error('Request failed'));
        }
        setIsLoading(false);
        setUploadProgress(0);
      });

      xhr.addEventListener('error', () => {
        setError('Network error occurred');
        setShowToast(true);
        setIsLoading(false);
        setUploadProgress(0);
        reject(new Error('Network error'));
      });

      xhr.addEventListener('abort', () => {
        setError('Upload cancelled');
        setShowToast(true);
        setIsLoading(false);
        setUploadProgress(0);
        reject(new Error('Upload cancelled'));
      });

      xhr.open('POST', '/api/summarize');
      xhr.send(formData);
    });
  };

  const handleCancel = () => {
    if (xhrRef.current) {
      xhrRef.current.abort();
    }
    setIsLoading(false);
    setUploadProgress(0);
  };

  const handleCloseToast = () => {
    setShowToast(false);
  };

  return {
    result,
    isLoading,
    responseTime,
    error,
    showToast,
    uploadProgress,
    handleSubmit,
    handleCancel,
    handleCloseToast,
  };
};
