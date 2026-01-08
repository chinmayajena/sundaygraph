'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Database, Network, Loader2, RefreshCw } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import Link from 'next/link'

export default function WorkspaceGraphPage() {
  const params = useParams()
  const workspaceId = params.workspaceId as string
  const [nodes, setNodes] = useState<any[]>([])
  const [edges, setEdges] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedEntityType, setSelectedEntityType] = useState<string>('')
  const [selectedRelationType, setSelectedRelationType] = useState<string>('')
  const { toast } = useToast()

  useEffect(() => {
    loadGraphData()
  }, [workspaceId, selectedEntityType, selectedRelationType])

  const loadGraphData = async () => {
    try {
      setLoading(true)
      const [nodesResponse, edgesResponse, statsResponse] = await Promise.all([
        apiClient.getGraphNodes(workspaceId, selectedEntityType || undefined, 100),
        apiClient.getGraphEdges(workspaceId, selectedRelationType || undefined, 100),
        apiClient.getStats(workspaceId)
      ])

      setNodes(nodesResponse?.data || nodesResponse || [])
      setEdges(edgesResponse?.data || edgesResponse || [])
      setStats(statsResponse?.data || statsResponse || null)
    } catch (error: any) {
      toast({
        title: "Error loading graph data",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  // Get unique entity types
  const entityTypes = Array.from(new Set(nodes.map(n => n.type || 'Unknown'))).filter(Boolean)
  const relationTypes = Array.from(new Set(edges.map(e => e.type || 'Unknown'))).filter(Boolean)

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Knowledge Graph</h1>
            <p className="text-muted-foreground">
              Hydrated graph for workspace: {workspaceId}
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={loadGraphData}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
            <Link href={`/workspaces/${workspaceId}/files`}>
              <Button variant="outline">Back to Files</Button>
            </Link>
          </div>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Graph Nodes</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{nodes.length}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.graph?.nodes || 0} total in system
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Graph Edges</CardTitle>
            <Network className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{edges.length}</div>
            <p className="text-xs text-muted-foreground">
              {stats?.graph?.edges || 0} total in system
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Entity Types</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{entityTypes.length}</div>
            <p className="text-xs text-muted-foreground">Unique types</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Graph Nodes (Entities)</CardTitle>
            <CardDescription>
              {nodes.length} entities in the knowledge graph
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <select
                value={selectedEntityType}
                onChange={(e) => setSelectedEntityType(e.target.value)}
                className="w-full p-2 border rounded"
              >
                <option value="">All Entity Types</option>
                {entityTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2 max-h-96 overflow-auto">
              {nodes.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No entities found. Ingest files to populate the graph.</p>
                  <Link href={`/workspaces/${workspaceId}/files`}>
                    <Button variant="outline" className="mt-4">
                      Go to Files
                    </Button>
                  </Link>
                </div>
              ) : (
                nodes.map((node, idx) => (
                  <div key={idx} className="p-3 border rounded">
                    <div className="font-medium">{node.id || node.name || `Entity ${idx + 1}`}</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      Type: {node.type || 'Unknown'}
                    </div>
                    {Object.keys(node).filter(k => !['id', 'type', 'name'].includes(k)).length > 0 && (
                      <div className="text-xs text-muted-foreground mt-2">
                        {Object.entries(node)
                          .filter(([k]) => !['id', 'type', 'name'].includes(k))
                          .slice(0, 3)
                          .map(([k, v]) => `${k}: ${String(v).substring(0, 30)}`)
                          .join(', ')}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Graph Edges (Relations)</CardTitle>
            <CardDescription>
              {edges.length} relations in the knowledge graph
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="mb-4">
              <select
                value={selectedRelationType}
                onChange={(e) => setSelectedRelationType(e.target.value)}
                className="w-full p-2 border rounded"
              >
                <option value="">All Relation Types</option>
                {relationTypes.map(type => (
                  <option key={type} value={type}>{type}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2 max-h-96 overflow-auto">
              {edges.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>No relations found. Ingest files to create relationships.</p>
                  <Link href={`/workspaces/${workspaceId}/files`}>
                    <Button variant="outline" className="mt-4">
                      Go to Files
                    </Button>
                  </Link>
                </div>
              ) : (
                edges.map((edge, idx) => (
                  <div key={idx} className="p-3 border rounded">
                    <div className="font-medium">{edge.type || 'Relation'}</div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {edge.source} → {edge.target}
                    </div>
                    {edge.properties && Object.keys(edge.properties).length > 0 && (
                      <div className="text-xs text-muted-foreground mt-2">
                        {Object.entries(edge.properties)
                          .slice(0, 3)
                          .map(([k, v]) => `${k}: ${String(v).substring(0, 30)}`)
                          .join(', ')}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Graph Storage Information</CardTitle>
          <CardDescription>Where the hydrated graph is stored</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Storage Backend:</span>
              <span className="font-medium">{stats?.graph?.backend || 'memory'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Nodes:</span>
              <span className="font-medium">{stats?.graph?.nodes || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Total Edges:</span>
              <span className="font-medium">{stats?.graph?.edges || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Entity Types:</span>
              <span className="font-medium">{stats?.graph?.entity_types || 0}</span>
            </div>
            <div className="mt-4 p-3 bg-muted rounded">
              <p className="text-xs text-muted-foreground">
                <strong>Memory Backend:</strong> Graph is stored in-memory using NetworkX. 
                Data is lost when the server restarts unless persisted to disk.
              </p>
              <p className="text-xs text-muted-foreground mt-2">
                <strong>Neo4j Backend:</strong> Graph is stored in Neo4j database. 
                Data persists across restarts. Configure in config.yaml to use Neo4j.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
