'use client'

import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataInput } from '@/components/data-input'

export default function SchemaPage() {
  const params = useParams()
  const workspaceId = params.workspaceId as string

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Schema Management</h1>
        <p className="text-muted-foreground">
          Build and manage ontology schema for workspace: {workspaceId}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Build Ontology Schema</CardTitle>
          <CardDescription>
            Describe your domain and let AI build the ontology schema automatically
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataInput />
        </CardContent>
      </Card>
    </div>
  )
}
