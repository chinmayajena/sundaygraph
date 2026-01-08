'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Database, FolderOpen, FileText, Search, TrendingUp, Loader2 } from "lucide-react"
import { apiClient } from '@/lib/api'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'

interface Workspace {
  id: string
  name: string
  description?: string
  created_at: string
  fileCount?: number
}

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [totalFiles, setTotalFiles] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
    // Refresh data every 30 seconds
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch stats and workspaces in parallel
      // Handle workspaces endpoint gracefully if it doesn't exist yet (backend needs restart)
      const [statsResponse, workspacesResponse] = await Promise.allSettled([
        apiClient.getStats().catch((err) => {
          console.error('Failed to fetch stats:', err)
          return { data: null }
        }),
        apiClient.getWorkspaces().catch((err) => {
          // Workspace endpoint might not be available if backend wasn't restarted
          console.warn('Workspaces endpoint not available (backend may need restart):', err)
          return { data: [] }
        })
      ])

      // Extract stats data
      const statsData = statsResponse.status === 'fulfilled' 
        ? (statsResponse.value?.data || statsResponse.value || null)
        : null

      // Extract workspaces data
      const workspacesData = workspacesResponse.status === 'fulfilled'
        ? (workspacesResponse.value?.data || workspacesResponse.value || [])
        : []

      setStats(statsData)
      setWorkspaces(workspacesData)

      // Calculate total files across all workspaces
      // Only if we have workspaces data
      let total = 0
      if (workspacesData && Array.isArray(workspacesData) && workspacesData.length > 0) {
        try {
          const workspacesWithFiles = await Promise.all(
            workspacesData.map(async (workspace: Workspace) => {
              try {
                const filesResponse = await apiClient.listWorkspaceFiles(workspace.id, 'input')
                // filesResponse is already the API response {success, message, data}
                const fileCount = filesResponse?.data?.length || filesResponse?.length || 0
                total += fileCount
                return { ...workspace, fileCount }
              } catch (err) {
                // If file listing fails, just set count to 0
                console.warn(`Failed to get files for workspace ${workspace.id}:`, err)
                return { ...workspace, fileCount: 0 }
              }
            })
          )
          setWorkspaces(workspacesWithFiles)
        } catch (err) {
          // If file listing completely fails, just use workspaces without file counts
          console.warn('Failed to get file counts:', err)
          setWorkspaces(workspacesData.map((w: Workspace) => ({ ...w, fileCount: 0 })))
        }
      } else {
        setWorkspaces([])
      }
      setTotalFiles(total)
    } catch (err: any) {
      console.error('Error loading dashboard data:', err)
      setError(err.message || 'Failed to load dashboard data')
      toast({
        title: "Error loading dashboard",
        description: err.message || "Failed to fetch dashboard data",
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">Loading dashboard data...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-8">
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-destructive mb-4">{error}</p>
            <Button onClick={loadData}>Retry</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Extract stats with proper fallbacks
  const graphNodes = stats?.graph?.nodes ?? 0
  const graphEdges = stats?.graph?.edges ?? 0
  const entityTypes = stats?.ontology?.entities ?? 0
  const relationTypes = stats?.ontology?.relations ?? 0
  const entityTypeCount = stats?.graph?.entity_types ?? 0

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
        <p className="text-muted-foreground">
          Overview of your knowledge graph system
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Link href="/workspaces">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Workspaces</CardTitle>
              <FolderOpen className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{workspaces.length}</div>
              <p className="text-xs text-muted-foreground">Active workspaces</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/files">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Files</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalFiles}</div>
              <p className="text-xs text-muted-foreground">Files across workspaces</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/graph">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Graph Nodes</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{graphNodes}</div>
              <p className="text-xs text-muted-foreground">Entities in graph</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/graph">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Relations</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{graphEdges}</div>
              <p className="text-xs text-muted-foreground">Relationships</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Link href="/ontology">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Entity Types</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{entityTypes}</div>
              <p className="text-xs text-muted-foreground">Defined in ontology</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/ontology">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Relation Types</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{relationTypes}</div>
              <p className="text-xs text-muted-foreground">Defined in ontology</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/graph">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Entity Instances</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{entityTypeCount}</div>
              <p className="text-xs text-muted-foreground">Unique entity types in graph</p>
            </CardContent>
          </Card>
        </Link>

        <Link href="/agents">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Agents</CardTitle>
              <Search className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats?.agents ? Object.keys(stats.agents).length : 0}
              </div>
              <p className="text-xs text-muted-foreground">Active agents</p>
            </CardContent>
          </Card>
        </Link>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link href="/workspaces">
              <Button variant="outline" className="w-full justify-start">
                <FolderOpen className="h-4 w-4 mr-2" />
                Manage Workspaces
              </Button>
            </Link>
            {workspaces.length > 0 && (
              <Link href={`/workspaces/${workspaces[0].id}/files`}>
                <Button variant="outline" className="w-full justify-start">
                  <FileText className="h-4 w-4 mr-2" />
                  View Files
                </Button>
              </Link>
            )}
            {workspaces.length > 0 && (
              <Link href={`/workspaces/${workspaces[0].id}/query`}>
                <Button variant="outline" className="w-full justify-start">
                  <Search className="h-4 w-4 mr-2" />
                  Query Graph
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Workspaces</CardTitle>
            <CardDescription>Your workspaces with file counts</CardDescription>
          </CardHeader>
          <CardContent>
            {workspaces.length === 0 ? (
              <div className="text-center py-4 text-muted-foreground">
                <p className="mb-2">No workspaces yet</p>
                <Link href="/workspaces">
                  <Button size="sm">Create Workspace</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-2">
                {workspaces.slice(0, 5).map((workspace) => (
                  <Link key={workspace.id} href={`/workspaces/${workspace.id}/files`}>
                    <div className="p-3 border rounded hover:bg-accent cursor-pointer transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="font-medium">{workspace.name}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {workspace.id}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-semibold">
                            {workspace.fileCount ?? 0}
                          </div>
                          <div className="text-xs text-muted-foreground">files</div>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

