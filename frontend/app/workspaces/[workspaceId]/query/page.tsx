'use client'

import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataView } from '@/components/data-view'

export default function QueryPage() {
  const params = useParams()
  const workspaceId = params.workspaceId as string

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Query Graph</h1>
        <p className="text-muted-foreground">
          Search and explore the knowledge graph for workspace: {workspaceId}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Graph Query</CardTitle>
          <CardDescription>
            Query entities, relations, and paths in the knowledge graph
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataView />
        </CardContent>
      </Card>
    </div>
  )
}
