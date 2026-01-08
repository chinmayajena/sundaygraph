'use client'

import { Card, CardContent } from '@/components/ui/card'
import { formatFileSize } from '@/lib/utils'

interface FilePreviewProps {
  data: {
    name: string
    size: number
    modified: string
    extension: string
    type: string
    preview?: string
    preview_type?: string
  }
}

export function FilePreview({ data }: FilePreviewProps) {
  const renderPreview = () => {
    if (!data.preview) {
      return <div className="text-muted-foreground">No preview available</div>
    }

    if (data.preview_type === 'json') {
      try {
        const json = JSON.parse(data.preview)
        return (
          <pre className="bg-muted p-4 rounded overflow-auto text-sm">
            {JSON.stringify(json, null, 2)}
          </pre>
        )
      } catch {
        return (
          <pre className="bg-muted p-4 rounded overflow-auto text-sm">
            {data.preview}
          </pre>
        )
      }
    }

    if (data.preview_type === 'text') {
      return (
        <pre className="bg-muted p-4 rounded overflow-auto text-sm whitespace-pre-wrap">
          {data.preview}
        </pre>
      )
    }

    return (
      <div className="text-muted-foreground p-4 bg-muted rounded">
        {data.preview}
      </div>
    )
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
          <span>{data.type}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-muted-foreground">Modified:</span>
          <span>{new Date(data.modified).toLocaleString()}</span>
        </div>
      </div>

      <div className="border-t pt-4">
        <div className="text-sm font-medium mb-2">Preview:</div>
        <div className="max-h-96 overflow-auto">
          {renderPreview()}
        </div>
      </div>
    </div>
  )
}
