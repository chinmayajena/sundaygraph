'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Upload, Eye, Download, Database, Sparkles } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import { FilePreview } from '@/components/file-preview'

interface FileInfo {
  name: string
  path: string
  size: number
  modified: string
  extension: string
  type: string
}

export default function FilesPage() {
  const params = useParams()
  const workspaceId = params.workspaceId as string
  const [files, setFiles] = useState<FileInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [previewData, setPreviewData] = useState<any>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [selectedFilesForIngest, setSelectedFilesForIngest] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  useEffect(() => {
    if (workspaceId) {
      loadFiles()
    }
  }, [workspaceId])

  const loadFiles = async () => {
    try {
      setLoading(true)
      const result = await apiClient.listWorkspaceFiles(workspaceId, 'input')
      setFiles(result.data || [])
    } catch (error: any) {
      toast({
        title: "Error loading files",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = async (filename: string) => {
    setSelectedFile(filename)
    setLoadingPreview(true)
    try {
      const result = await apiClient.getFilePreview(workspaceId, filename, 'input')
      // Ensure file_path is included for PDF files and add workspaceId
      const previewData = result.data
      if (previewData) {
        if (!previewData.file_path && previewData.path) {
          previewData.file_path = previewData.path
        }
        previewData.workspaceId = workspaceId
      }
      setPreviewData(previewData)
    } catch (error: any) {
      toast({
        title: "Error loading preview",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setLoadingPreview(false)
    }
  }

  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files
    if (!selectedFiles || selectedFiles.length === 0) return

    try {
      const fileArray = Array.from(selectedFiles)
      await apiClient.uploadWorkspaceFiles(workspaceId, fileArray)
      toast({
        title: "Files uploaded",
        description: `Uploaded ${fileArray.length} file(s) successfully`,
      })
      loadFiles()
      // Reset input so same file can be uploaded again
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    } catch (error: any) {
      toast({
        title: "Error uploading files",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    }
  }

  const handleIngestFiles = async (filenames: string[] = []) => {
    try {
      setIngesting(true)
      const result = await apiClient.ingestWorkspaceFiles(workspaceId, filenames)
      toast({
        title: "Files ingested successfully",
        description: `Processed ${result.data?.files_processed || 0} file(s). Added ${result.data?.total_entities || 0} entities and ${result.data?.total_relations || 0} relations to graph.`,
      })
      setSelectedFilesForIngest([])
    } catch (error: any) {
      toast({
        title: "Error ingesting files",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    } finally {
      setIngesting(false)
    }
  }

  const toggleFileForIngest = (filename: string) => {
    setSelectedFilesForIngest(prev => 
      prev.includes(filename) 
        ? prev.filter(f => f !== filename)
        : [...prev, filename]
    )
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Files</h1>
        <p className="text-muted-foreground">
          Manage and preview files in workspace: {workspaceId}
        </p>
      </div>

      <div className="mb-4 flex gap-2">
        <Button 
          variant="outline" 
          onClick={handleUploadClick}
          type="button"
        >
          <Upload className="h-4 w-4 mr-2" />
          Upload Files
        </Button>
        <Button 
          variant="default" 
          onClick={() => {
            // If no files selected, pass empty array to ingest all files
            handleIngestFiles(selectedFilesForIngest.length > 0 ? selectedFilesForIngest : [])
          }}
          disabled={ingesting || files.length === 0}
          type="button"
        >
          <Database className="h-4 w-4 mr-2" />
          {ingesting ? 'Ingesting...' : selectedFilesForIngest.length > 0 
            ? `Ingest Selected (${selectedFilesForIngest.length})` 
            : 'Ingest All Files'}
        </Button>
        <Button 
          variant="outline" 
          onClick={async () => {
            try {
              setIngesting(true)
              // If no files selected, pass empty array to use all files
              const filesToUse = selectedFilesForIngest.length > 0 ? selectedFilesForIngest : []
              const result = await apiClient.buildOntologyFromFiles(workspaceId, filesToUse)
              toast({
                title: "Ontology built successfully",
                description: `Created schema with ${result.data?.entities || 0} entity types and ${result.data?.relations || 0} relation types`,
              })
              setSelectedFilesForIngest([])
            } catch (error: any) {
              toast({
                title: "Error building ontology",
                description: error.response?.data?.detail || error.message,
                variant: "destructive",
              })
            } finally {
              setIngesting(false)
            }
          }}
          disabled={ingesting || files.length === 0}
          type="button"
        >
          <Sparkles className="h-4 w-4 mr-2" />
          Build Ontology from Files
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileUpload}
          className="hidden"
          accept=".json,.csv,.txt,.xml,.pdf,.docx"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>File List</CardTitle>
            <CardDescription>
              {files.length} file(s) in workspace
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8 text-muted-foreground">Loading files...</div>
            ) : files.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No files found. Upload files to get started.</p>
              </div>
            ) : (
              <div className="space-y-2">
                {files.map((file) => {
                  const isSelected = selectedFile === file.name
                  const isSelectedForIngest = selectedFilesForIngest.includes(file.name)
                  return (
                    <div
                      key={file.name}
                      className={`p-3 border rounded-lg transition-colors ${
                        isSelected
                          ? 'bg-primary text-primary-foreground'
                          : isSelectedForIngest
                          ? 'bg-accent border-primary'
                          : 'hover:bg-accent'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div 
                          className="flex-1 cursor-pointer"
                          onClick={() => handleFileSelect(file.name)}
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4" />
                            <span className="font-medium">{file.name}</span>
                            {isSelectedForIngest && (
                              <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded">
                                Selected
                              </span>
                            )}
                          </div>
                          <div className="text-xs mt-1 opacity-80">
                            {formatFileSize(file.size)} • {new Date(file.modified).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              handleFileSelect(file.name)
                            }}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant={isSelectedForIngest ? "default" : "ghost"}
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              toggleFileForIngest(file.name)
                            }}
                            title={isSelectedForIngest ? "Deselect for ingestion" : "Select for ingestion"}
                          >
                            <Database className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>File Preview</CardTitle>
            <CardDescription>
              {selectedFile ? `Previewing: ${selectedFile}` : 'Select a file to preview'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {loadingPreview ? (
              <div className="text-center py-8 text-muted-foreground">Loading preview...</div>
            ) : previewData ? (
              <FilePreview data={previewData} />
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Eye className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Select a file from the list to view its preview</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
