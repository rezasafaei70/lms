/**
 * S3 Multipart Upload Client
 * 
 * Usage:
 * 
 * const uploader = new S3MultipartUploader({
 *     apiBaseUrl: '/api/v1/files',
 *     token: 'your-jwt-token',
 *     onProgress: (percent) => console.log(`Progress: ${percent}%`),
 *     onComplete: (result) => console.log('Upload complete:', result),
 *     onError: (error) => console.error('Upload failed:', error)
 * });
 * 
 * uploader.upload(file, { folder: 'courses/videos' });
 */

class S3MultipartUploader {
    constructor(options) {
        this.apiBaseUrl = options.apiBaseUrl || '/api/v1/files';
        this.token = options.token;
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
        this.onPartComplete = options.onPartComplete || (() => {});
        
        // Concurrent upload settings
        this.concurrentUploads = options.concurrentUploads || 3;
        
        // Internal state
        this.uploadId = null;
        this.s3UploadId = null;
        this.s3Key = null;
        this.parts = [];
        this.aborted = false;
    }
    
    /**
     * Get authorization headers
     */
    getHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json',
        };
    }
    
    /**
     * Upload a file
     * 
     * @param {File} file - The file to upload
     * @param {Object} options - Upload options
     * @param {string} options.folder - Target folder in S3
     * @param {string} options.targetModel - Model name (optional)
     * @param {string} options.targetField - Field name (optional)
     * @param {string} options.targetObjectId - Object ID (optional)
     */
    async upload(file, options = {}) {
        this.aborted = false;
        this.parts = [];
        
        const folder = options.folder || 'uploads';
        
        try {
            // Step 1: Initiate upload
            const initResponse = await this.initiateUpload(file, folder, options);
            
            if (this.aborted) return;
            
            this.uploadId = initResponse.upload_id;
            this.s3UploadId = initResponse.s3_upload_id;
            this.s3Key = initResponse.s3_key;
            
            const { presigned_urls, part_size, total_parts } = initResponse;
            
            // Step 2: Upload parts
            await this.uploadParts(file, presigned_urls, part_size, total_parts);
            
            if (this.aborted) return;
            
            // Step 3: Complete upload
            const result = await this.completeUpload();
            
            this.onComplete(result);
            return result;
            
        } catch (error) {
            if (!this.aborted) {
                await this.abortUpload();
                this.onError(error);
            }
            throw error;
        }
    }
    
    /**
     * Initiate multipart upload
     */
    async initiateUpload(file, folder, options) {
        const response = await fetch(`${this.apiBaseUrl}/initiate/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({
                filename: file.name,
                content_type: file.type || 'application/octet-stream',
                file_size: file.size,
                target_folder: folder,
                target_model: options.targetModel || '',
                target_field: options.targetField || '',
                target_object_id: options.targetObjectId || '',
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to initiate upload');
        }
        
        return response.json();
    }
    
    /**
     * Upload parts concurrently
     */
    async uploadParts(file, presignedUrls, partSize, totalParts) {
        const uploadPromises = [];
        let completedParts = 0;
        
        const uploadPart = async (partInfo, partNumber) => {
            if (this.aborted) return;
            
            const start = (partNumber - 1) * partSize;
            const end = Math.min(partNumber * partSize, file.size);
            const chunk = file.slice(start, end);
            
            // Upload directly to S3 using presigned URL
            const response = await fetch(partInfo.presigned_url, {
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
            const etag = response.headers.get('ETag');
            
            // Report part completion to backend
            await this.reportPartCompletion(partNumber, etag);
            
            this.parts.push({
                part_number: partNumber,
                etag: etag,
            });
            
            completedParts++;
            const progress = Math.round((completedParts / totalParts) * 100);
            this.onProgress(progress);
            this.onPartComplete(partNumber, totalParts);
        };
        
        // Upload parts with concurrency limit
        const chunks = [];
        for (let i = 0; i < presignedUrls.length; i += this.concurrentUploads) {
            chunks.push(presignedUrls.slice(i, i + this.concurrentUploads));
        }
        
        for (const chunk of chunks) {
            if (this.aborted) break;
            
            await Promise.all(
                chunk.map(partInfo => uploadPart(partInfo, partInfo.part_number))
            );
        }
    }
    
    /**
     * Report part completion to backend
     */
    async reportPartCompletion(partNumber, etag) {
        const response = await fetch(`${this.apiBaseUrl}/report-part/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({
                upload_id: this.uploadId,
                part_number: partNumber,
                etag: etag,
            }),
        });
        
        if (!response.ok) {
            console.warn(`Failed to report part ${partNumber} completion`);
        }
    }
    
    /**
     * Complete multipart upload
     */
    async completeUpload() {
        const response = await fetch(`${this.apiBaseUrl}/complete/`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({
                upload_id: this.uploadId,
                parts: this.parts.sort((a, b) => a.part_number - b.part_number),
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to complete upload');
        }
        
        return response.json();
    }
    
    /**
     * Abort upload
     */
    async abortUpload() {
        this.aborted = true;
        
        if (!this.uploadId) return;
        
        try {
            await fetch(`${this.apiBaseUrl}/abort/`, {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({
                    upload_id: this.uploadId,
                }),
            });
        } catch (error) {
            console.error('Failed to abort upload:', error);
        }
    }
    
    /**
     * Get upload status
     */
    async getStatus() {
        if (!this.uploadId) return null;
        
        const response = await fetch(`${this.apiBaseUrl}/status/${this.uploadId}/`, {
            method: 'GET',
            headers: this.getHeaders(),
        });
        
        if (!response.ok) {
            throw new Error('Failed to get upload status');
        }
        
        return response.json();
    }
}


/**
 * Simple file upload (for small files)
 */
class SimpleUploader {
    constructor(options) {
        this.apiBaseUrl = options.apiBaseUrl || '/api/v1/files';
        this.token = options.token;
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
    }
    
    async upload(file, options = {}) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('folder', options.folder || 'uploads');
        
        if (options.targetModel) formData.append('target_model', options.targetModel);
        if (options.targetField) formData.append('target_field', options.targetField);
        if (options.targetObjectId) formData.append('target_object_id', options.targetObjectId);
        
        try {
            const xhr = new XMLHttpRequest();
            
            return new Promise((resolve, reject) => {
                xhr.upload.addEventListener('progress', (e) => {
                    if (e.lengthComputable) {
                        const percent = Math.round((e.loaded / e.total) * 100);
                        this.onProgress(percent);
                    }
                });
                
                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        const result = JSON.parse(xhr.responseText);
                        this.onComplete(result);
                        resolve(result);
                    } else {
                        const error = JSON.parse(xhr.responseText);
                        this.onError(error);
                        reject(new Error(error.error || 'Upload failed'));
                    }
                });
                
                xhr.addEventListener('error', () => {
                    this.onError({ message: 'Network error' });
                    reject(new Error('Network error'));
                });
                
                xhr.open('POST', `${this.apiBaseUrl}/simple/`);
                xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
                xhr.send(formData);
            });
            
        } catch (error) {
            this.onError(error);
            throw error;
        }
    }
}


/**
 * Auto-select uploader based on file size
 */
class FileUploader {
    constructor(options) {
        this.options = options;
        this.threshold = options.multipartThreshold || 5 * 1024 * 1024; // 5MB
    }
    
    async upload(file, uploadOptions = {}) {
        if (file.size > this.threshold) {
            const uploader = new S3MultipartUploader(this.options);
            return uploader.upload(file, uploadOptions);
        } else {
            const uploader = new SimpleUploader(this.options);
            return uploader.upload(file, uploadOptions);
        }
    }
}


// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { S3MultipartUploader, SimpleUploader, FileUploader };
}

