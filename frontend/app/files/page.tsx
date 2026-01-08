'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Loader2, FolderOpen } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

interface Workspace {
  id: string
  name: string
  fileCount?: number
}

export default function FilesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [totalFiles, setTotalFiles] = useState(0)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const workspacesResponse = await apiClient.getWorkspaces()
      const workspacesData = workspacesResponse?.data || []

      let total = 0
      const workspacesWithFiles = await Promise.all(
        workspacesData.map(async (workspace: Workspace) => {
          try {
            const filesResponse = await apiClient.listWorkspaceFiles(workspace.id, 'input')
            const fileCount = filesResponse?.data?.length || filesResponse?.length || 0
            total += fileCount
            return { ...workspace, fileCount }
          } catch {
            return { ...workspace, fileCount: 0 }
          }
        })
      )

      setWorkspaces(workspacesWithFiles)
      setTotalFiles(total)
    } catch (err: any) {
      console.error('Error loading files data:', err)
      toast({
        title: "Error loading files",
        description: err.message || "Failed to fetch files data",
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
            <h1 className="text-3xl font-bold mb-2">Files Overview</h1>
            <p className="text-muted-foreground">
              All files across all workspaces
            </p>
          </div>
          <Link href="/">
            <Button variant="outline">Back to Dashboard</Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Files</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalFiles}</div>
            <p className="text-xs text-muted-foreground">Across all workspaces</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Workspaces</CardTitle>
            <FolderOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{workspaces.length}</div>
            <p className="text-xs text-muted-foreground">With files</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Files by Workspace</CardTitle>
          <CardDescription>Browse files in each workspace</CardDescription>
        </CardHeader>
        <CardContent>
          {workspaces.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <p className="mb-4">No workspaces with files yet</p>
              <Link href="/workspaces">
                <Button>Create Workspace</Button>
              </Link>
            </div>
          ) : (
            <div className="space-y-4">
              {workspaces.map((workspace) => (
                <Link key={workspace.id} href={`/workspaces/${workspace.id}/files`}>
                  <div className="p-4 border rounded hover:bg-accent cursor-pointer transition-colors">
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="font-medium">{workspace.name}</div>
                        <div className="text-sm text-muted-foreground mt-1">
                          {workspace.id}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-lg font-semibold">
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
  )
}
