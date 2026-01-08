'use client'

import { useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

export function DataInput() {
  const [domainDescription, setDomainDescription] = useState('')
  const [textData, setTextData] = useState('')
  const [loading, setLoading] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const { toast } = useToast()

  const onDrop = (acceptedFiles: File[]) => {
    setUploadedFiles(prev => [...prev, ...acceptedFiles])
    toast({
      title: "Files uploaded",
      description: `${acceptedFiles.length} file(s) ready for processing`,
    })
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/json': ['.json'],
      'text/csv': ['.csv'],
      'text/plain': ['.txt'],
      'application/xml': ['.xml'],
      'application/pdf': ['.pdf'],
    },
  })

  const handleBuildSchema = async () => {
    if (!domainDescription.trim()) {
      toast({
        title: "Error",
        description: "Please provide a domain description",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      const result = await apiClient.buildSchema({ domain_description: domainDescription })
      toast({
        title: "Schema built successfully",
        description: `Created ${result.data?.entities || 0} entities and ${result.data?.relations || 0} relations`,
      })
    } catch (error: any) {
      toast({
        title: "Error building schema",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleIngestData = async () => {
    if (uploadedFiles.length === 0 && !textData.trim()) {
      toast({
        title: "Error",
        description: "Please upload files or provide text data",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      if (textData.trim()) {
        // Ingest text directly
        const result = await apiClient.ingestText({ text: textData })
        toast({
          title: "Data ingested successfully",
          description: `Processed ${result.data?.entities_added || 0} entities`,
        })
        setTextData('')
      } else if (uploadedFiles.length > 0) {
        // Upload files first, then ingest
        const formData = new FormData()
        uploadedFiles.forEach(file => {
          formData.append('files', file)
        })
        
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const uploadResponse = await fetch(`${apiUrl}/api/v1/upload`, {
          method: 'POST',
          body: formData,
        })
        
        if (!uploadResponse.ok) {
          const error = await uploadResponse.json().catch(() => ({ detail: 'File upload failed' }))
          throw new Error(error.detail || 'File upload failed')
        }
        
        const uploadResult = await uploadResponse.json()
        const paths = uploadResult.data?.paths || []
        
        // Ingest each uploaded file
        let totalEntities = 0
        for (const path of paths) {
          const result = await apiClient.ingestData({ input_path: path })
          totalEntities += result.data?.entities_added || 0
        }
        
        toast({
          title: "Files ingested successfully",
          description: `Processed ${uploadedFiles.length} file(s), added ${totalEntities} entities`,
        })
        setUploadedFiles([])
      }
    } catch (error: any) {
      toast({
        title: "Error ingesting data",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Build Ontology Schema</CardTitle>
          <CardDescription>
            Describe your domain and let AI build the ontology schema automatically
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="domain">Domain Description</Label>
            <Textarea
              id="domain"
              placeholder="e.g., A knowledge graph for a software company with employees, projects, technologies, and skills..."
              value={domainDescription}
              onChange={(e) => setDomainDescription(e.target.value)}
              rows={4}
            />
          </div>
          <Button onClick={handleBuildSchema} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Building Schema...
              </>
            ) : (
              'Build Schema with AI'
            )}
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ingest Data</CardTitle>
          <CardDescription>
            Upload files or paste text to populate the knowledge graph
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Upload Files</Label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                isDragActive ? 'border-primary bg-primary/5' : 'border-muted'
              }`}
            >
              <input {...getInputProps()} />
              <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              {isDragActive ? (
                <p>Drop files here...</p>
              ) : (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">
                    Drag & drop files here, or click to select
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Supports: JSON, CSV, TXT, XML, PDF
                  </p>
                </div>
              )}
            </div>
            {uploadedFiles.length > 0 && (
              <div className="mt-2 space-y-1">
                {uploadedFiles.map((file, idx) => (
                  <div key={idx} className="flex items-center gap-2 text-sm">
                    <FileText className="h-4 w-4" />
                    <span>{file.name}</span>
                    <span className="text-muted-foreground">
                      ({(file.size / 1024).toFixed(2)} KB)
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="text-data">Or Paste Text Data</Label>
            <Textarea
              id="text-data"
              placeholder="Paste your structured or unstructured text data here..."
              value={textData}
              onChange={(e) => setTextData(e.target.value)}
              rows={6}
            />
          </div>

          <Button onClick={handleIngestData} disabled={loading || (uploadedFiles.length === 0 && !textData.trim())}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing...
              </>
            ) : (
              'Ingest Data'
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

