import { useState, useCallback, useRef } from 'react';
import { filesAPI } from '../services/api';

// Default chunk size: 5MB (minimum for S3 multipart)
const DEFAULT_CHUNK_SIZE = 5 * 1024 * 1024;
// Threshold for multipart upload: 5MB
const MULTIPART_THRESHOLD = 5 * 1024 * 1024;

/**
 * Hook for uploading files to S3
 * Automatically uses multipart upload for files > 5MB
 */
export const useS3Upload = (options = {}) => {
  const {
    chunkSize = DEFAULT_CHUNK_SIZE,
    onProgress,
    onComplete,
    onError,
    targetFolder = 'uploads',
    targetModel = '',
    targetField = '',
    targetObjectId = '',
  } = options;

  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const abortControllerRef = useRef(null);
  const uploadIdRef = useRef(null);

  /**
   * Simple upload for small files (< 5MB)
   */
  const simpleUpload = useCallback(async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', targetFolder);
    
    if (targetModel) formData.append('target_model', targetModel);
    if (targetField) formData.append('target_field', targetField);
    if (targetObjectId) formData.append('target_object_id', targetObjectId);

    const response = await filesAPI.simpleUpload(formData);
    return response.data;
  }, [targetFolder, targetModel, targetField, targetObjectId]);

  /**
   * Upload a single part to S3 using presigned URL
   */
  const uploadPart = async (file, presignedUrl, partNumber, start, end) => {
    const chunk = file.slice(start, end);
    
    const response = await fetch(presignedUrl, {
      method: 'PUT',
      body: chunk,
      headers: {
        'Content-Type': file.type || 'application/octet-stream',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to upload part ${partNumber}`);
    }

    // Get ETag from response headers
    const etag = response.headers.get('ETag')?.replace(/"/g, '');
    return { partNumber, etag };
  };

  /**
   * Multipart upload for large files (>= 5MB)
   */
  const multipartUpload = useCallback(async (file) => {
    // Step 1: Initiate upload
    const initiateResponse = await filesAPI.initiateUpload({
      filename: file.name,
      content_type: file.type || 'application/octet-stream',
      file_size: file.size,
      target_folder: targetFolder,
      target_model: targetModel,
      target_field: targetField,
      target_object_id: targetObjectId,
    });

    const {
      upload_id,
      s3_upload_id,
      s3_key,
      part_size,
      total_parts,
      presigned_urls,
    } = initiateResponse.data;

    uploadIdRef.current = upload_id;

    // Step 2: Upload all parts
    const uploadedParts = [];
    let uploadedBytes = 0;

    for (let i = 0; i < total_parts; i++) {
      const partNumber = i + 1;
      const start = i * part_size;
      const end = Math.min(start + part_size, file.size);
      
      // Upload the part
      const partResult = await uploadPart(
        file,
        presigned_urls[i].url,
        partNumber,
        start,
        end
      );

      uploadedParts.push({
        part_number: partResult.partNumber,
        etag: partResult.etag,
      });

      // Report progress to backend
      await filesAPI.reportPart({
        upload_id,
        part_number: partResult.partNumber,
        etag: partResult.etag,
      });

      // Update progress
      uploadedBytes += (end - start);
      const progressPercent = Math.round((uploadedBytes / file.size) * 100);
      setProgress(progressPercent);
      if (onProgress) {
        onProgress(progressPercent, uploadedBytes, file.size);
      }
    }

    // Step 3: Complete upload
    const completeResponse = await filesAPI.completeUpload({
      upload_id,
      parts: uploadedParts,
    });

    return completeResponse.data;
  }, [targetFolder, targetModel, targetField, targetObjectId, onProgress]);

  /**
   * Main upload function - automatically chooses simple or multipart
   */
  const upload = useCallback(async (file) => {
    if (!file) {
      setError('فایلی انتخاب نشده است');
      return null;
    }

    setUploading(true);
    setProgress(0);
    setError(null);
    setUploadedFile(null);
    abortControllerRef.current = new AbortController();

    try {
      let result;

      if (file.size < MULTIPART_THRESHOLD) {
        // Use simple upload for small files
        setProgress(50); // Show some progress
        result = await simpleUpload(file);
        setProgress(100);
      } else {
        // Use multipart upload for large files
        result = await multipartUpload(file);
      }

      setUploadedFile(result);
      if (onComplete) {
        onComplete(result);
      }
      return result;
    } catch (err) {
      console.error('Upload error:', err);
      const errorMessage = err.response?.data?.error || err.message || 'خطا در آپلود فایل';
      setError(errorMessage);
      if (onError) {
        onError(errorMessage);
      }
      return null;
    } finally {
      setUploading(false);
    }
  }, [simpleUpload, multipartUpload, onComplete, onError]);

  /**
   * Abort ongoing upload
   */
  const abort = useCallback(async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    if (uploadIdRef.current) {
      try {
        await filesAPI.abortUpload({ upload_id: uploadIdRef.current });
      } catch (err) {
        console.error('Failed to abort upload:', err);
      }
    }

    setUploading(false);
    setProgress(0);
    setError('آپلود لغو شد');
  }, []);

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    setUploading(false);
    setProgress(0);
    setError(null);
    setUploadedFile(null);
    uploadIdRef.current = null;
  }, []);

  return {
    upload,
    abort,
    reset,
    uploading,
    progress,
    error,
    uploadedFile,
  };
};

export default useS3Upload;

