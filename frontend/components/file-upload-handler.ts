/**
 * File upload handler for sending files to backend
 * In production, this would upload files to the server first,
 * then call the ingest endpoint with the file path
 */

import { apiClient } from '@/lib/api'

export async function uploadAndIngestFiles(files: File[]): Promise<void> {
  // For now, we'll create a FormData and send to a future upload endpoint
  // Then call ingest with the uploaded file paths
  
  // TODO: Implement file upload endpoint in FastAPI
  // For now, this is a placeholder that shows the pattern
  
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })
  
  // In production:
  // 1. Upload files to /api/v1/upload endpoint
  // 2. Get back file paths
  // 3. Call ingest with those paths
  
  // For now, we'll need to implement this in the backend
  throw new Error('File upload not yet implemented. Please use text input or implement upload endpoint.')
}

