'use client'

import { useState, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { formatFileSize } from '@/lib/utils'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface FilePreviewProps {
  data: {
    name: string
    size: number
    modified: string
    extension: string
    type: string
    preview?: string
    preview_type?: string
    file_path?: string
    path?: string
    workspaceId?: string
  }
}

export function FilePreview({ data }: FilePreviewProps) {
  const [jsonError, setJsonError] = useState<string | null>(null)

  // Determine file type from extension or preview_type
  const fileType = useMemo(() => {
    if (data.preview_type) {
      return data.preview_type.toLowerCase()
    }
    const ext = data.extension?.toLowerCase() || ''
    if (ext === '.json') return 'json'
    if (ext === '.csv') return 'csv'
    if (ext === '.pdf') return 'pdf'
    if (['.txt', '.md', '.log'].includes(ext)) return 'text'
    return 'text'
  }, [data.extension, data.preview_type])

  // Parse CSV data with proper handling of quoted values, commas, and newlines
  const parseCSV = (csvText: string): { headers: string[], rows: string[][] } => {
    if (!csvText || !csvText.trim()) return { headers: [], rows: [] }
    
    const lines: string[] = []
    let currentLine = ''
    let inQuotes = false
    
    // Handle multi-line quoted values
    for (let i = 0; i < csvText.length; i++) {
      const char = csvText[i]
      const nextChar = csvText[i + 1]
      
      if (char === '"') {
        if (inQuotes && nextChar === '"') {
          // Escaped quote
          currentLine += '"'
          i++ // Skip next quote
        } else {
          inQuotes = !inQuotes
          currentLine += char
        }
      } else if (char === '\n' && !inQuotes) {
        // End of line (only if not in quotes)
        if (currentLine.trim()) {
          lines.push(currentLine)
        }
        currentLine = ''
      } else {
        currentLine += char
      }
    }
    
    // Add last line if exists
    if (currentLine.trim()) {
      lines.push(currentLine)
    }
    
    if (lines.length === 0) return { headers: [], rows: [] }
    
    // Parse CSV line into values
    const parseCSVLine = (line: string): string[] => {
      const values: string[] = []
      let current = ''
      let inQuotes = false
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i]
        const nextChar = line[i + 1]
        
        if (char === '"') {
          if (inQuotes && nextChar === '"') {
            // Escaped quote
            current += '"'
            i++ // Skip next quote
          } else {
            inQuotes = !inQuotes
          }
        } else if (char === ',' && !inQuotes) {
          values.push(current.trim())
          current = ''
        } else {
          current += char
        }
      }
      
      // Add last value
      values.push(current.trim())
      
      // Remove surrounding quotes from values
      return values.map(v => {
        // Remove quotes only if the entire value is quoted
        if (v.startsWith('"') && v.endsWith('"') && v.length > 1) {
          return v.slice(1, -1).replace(/""/g, '"')
        }
        return v
      })
    }
    
    // Parse headers
    const headers = parseCSVLine(lines[0])
    
    // Parse rows
    const rows = lines.slice(1)
      .filter(line => line.trim()) // Skip empty lines
      .map(line => parseCSVLine(line))
      .filter(row => row.length > 0) // Skip rows with no data
    
    return { headers, rows }
  }

  const renderJSONView = () => {
    if (!data.preview) {
      return <div className="text-muted-foreground">No preview available</div>
    }

    try {
      const json = JSON.parse(data.preview)
      const formatted = JSON.stringify(json, null, 2)
      setJsonError(null)
      
      return (
        <div className="relative">
          <div className="bg-[#1e1e1e] text-[#d4d4d4] p-4 rounded-lg overflow-auto max-h-[600px] font-mono text-sm">
            <pre className="whitespace-pre-wrap">{formatted}</pre>
          </div>
          <div className="mt-2 text-xs text-muted-foreground">
            JSON Editor View • {formatted.split('\n').length} lines
          </div>
        </div>
      )
    } catch (error: any) {
      setJsonError(error.message)
      return (
        <div className="text-destructive">
          <p className="font-medium mb-2">Invalid JSON:</p>
          <p className="text-sm">{error.message}</p>
          <pre className="bg-muted p-4 rounded overflow-auto text-sm mt-4">
            {data.preview}
          </pre>
        </div>
      )
    }
  }

  const renderCSVView = () => {
    if (!data.preview) {
      return <div className="text-muted-foreground">No preview available</div>
    }

    try {
      const { headers, rows } = parseCSV(data.preview)
      
      if (headers.length === 0) {
        return (
          <div className="text-muted-foreground">
            Empty CSV file or unable to parse
          </div>
        )
      }

      return (
        <div className="relative">
          <div className="overflow-auto max-h-[600px] border rounded-lg bg-background">
            <table className="w-full border-collapse min-w-full">
              <thead className="bg-muted sticky top-0 z-10">
                <tr>
                  {headers.map((header, idx) => (
                    <th
                      key={idx}
                      className="border border-border px-4 py-3 text-left font-semibold text-sm bg-muted"
                    >
                      {header || `Column ${idx + 1}`}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-background">
                {rows.slice(0, 100).map((row, rowIdx) => (
                  <tr 
                    key={rowIdx} 
                    className="hover:bg-muted/50 transition-colors border-b border-border"
                  >
                    {headers.map((_, colIdx) => (
                      <td
                        key={colIdx}
                        className="border-r border-border px-4 py-2 text-sm last:border-r-0"
                      >
                        <div className="max-w-xs truncate" title={row[colIdx] || ''}>
                          {row[colIdx] || <span className="text-muted-foreground italic">—</span>}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {rows.length > 100 && (
            <div className="mt-2 text-xs text-muted-foreground">
              Showing first 100 rows of {rows.length} total rows
            </div>
          )}
          <div className="mt-2 text-xs text-muted-foreground flex items-center gap-4">
            <span>Tabular View</span>
            <span>•</span>
            <span>{rows.length} rows</span>
            <span>×</span>
            <span>{headers.length} columns</span>
          </div>
        </div>
      )
    } catch (error: any) {
      return (
        <div className="text-destructive">
          <p className="font-medium mb-2">Error parsing CSV:</p>
          <p className="text-sm">{error.message}</p>
          <pre className="bg-muted p-4 rounded overflow-auto text-sm mt-4 whitespace-pre-wrap">
            {data.preview}
          </pre>
        </div>
      )
    }
  }

  const renderPDFView = () => {
    // For PDF, we'll use an iframe to display the PDF
    const filename = data.name
    let pdfUrl: string | null = null
    
    // Try to get workspaceId from data first
    if (data.workspaceId) {
      pdfUrl = `/api/v1/workspaces/${data.workspaceId}/files/${encodeURIComponent(filename)}/download?subdir=input`
    } else if (data.file_path || data.path) {
      // Extract workspace_id from path (e.g., ./data/workspaces/test-workspace/input/file.pdf)
      const filePath = data.file_path || data.path || ''
      const normalizedPath = filePath.replace(/\\/g, '/')
      const pathMatch = normalizedPath.match(/workspaces\/([^\/]+)\/(input|output|cache|graphs)\/([^\/]+)/)
      if (pathMatch) {
        const workspaceId = pathMatch[1]
        const subdir = pathMatch[2]
        const fileName = pathMatch[3]
        pdfUrl = `/api/v1/workspaces/${workspaceId}/files/${encodeURIComponent(fileName)}/download?subdir=${subdir}`
      }
    }

    if (!pdfUrl) {
      return (
        <div className="text-muted-foreground">
          PDF preview not available. File path information missing.
          <div className="mt-2 text-xs">
            File: {data.name}
            {data.file_path && (
              <div className="mt-1">Path: {data.file_path}</div>
            )}
          </div>
        </div>
      )
    }

    return (
      <div className="relative w-full">
        <div className="border rounded-lg overflow-hidden bg-muted">
          <iframe
            src={pdfUrl}
            className="w-full h-[600px]"
            title="PDF Preview"
          />
        </div>
        <div className="mt-2 text-xs text-muted-foreground">
          PDF Viewer • Use browser controls to navigate
        </div>
      </div>
    )
  }

  const renderTextView = () => {
    if (!data.preview) {
      return <div className="text-muted-foreground">No preview available</div>
    }

    return (
      <div className="relative">
        <pre className="bg-muted p-4 rounded overflow-auto text-sm whitespace-pre-wrap max-h-[600px] font-mono">
          {data.preview}
        </pre>
        <div className="mt-2 text-xs text-muted-foreground">
          Text View • {data.preview.split('\n').length} lines
        </div>
      </div>
    )
  }

  const renderPreview = () => {
    switch (fileType) {
      case 'json':
        return renderJSONView()
      case 'csv':
        return renderCSVView()
      case 'pdf':
        return renderPDFView()
      case 'text':
      default:
        return renderTextView()
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">File Name:</span>
          <span className="font-medium">{data.name}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Size:</span>
          <span>{formatFileSize(data.size)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Type:</span>
          <span className="capitalize">{fileType}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Modified:</span>
          <span>{new Date(data.modified).toLocaleString()}</span>
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="text-sm font-medium mb-2">Preview:</div>
        <div className="w-full">
          {renderPreview()}
        </div>
      </div>
    </div>
  )
}
