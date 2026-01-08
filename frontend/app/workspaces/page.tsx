'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { FolderOpen, Plus, Trash2 } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import Link from 'next/link'

interface Workspace {
  id: string
  name: string
  description?: string
  created_at: string
}

export default function WorkspacesPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [formData, setFormData] = useState({ name: '', description: '' })
  const { toast } = useToast()

  useEffect(() => {
    loadWorkspaces()
  }, [])

  const loadWorkspaces = async () => {
    try {
      setLoading(true)
      const result = await apiClient.getWorkspaces()
      setWorkspaces(result.data || [])
    } catch (error: any) {
      toast({
        title: "Error loading workspaces",
        description: error.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      toast({
        title: "Error",
        description: "Workspace name is required",
        variant: "destructive",
      })
      return
    }

    const workspaceId = formData.name.toLowerCase().replace(/\s+/g, '-')
    try {
      await apiClient.createWorkspace({
        workspace_id: workspaceId,
        name: formData.name,
        description: formData.description || undefined,
      })
      toast({
        title: "Workspace created",
        description: `Workspace "${formData.name}" created successfully`,
      })
      setFormData({ name: '', description: '' })
      setShowCreateForm(false)
      loadWorkspaces()
    } catch (error: any) {
      toast({
        title: "Error creating workspace",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    }
  }

  const handleDelete = async (workspaceId: string, workspaceName: string) => {
    if (!confirm(`Are you sure you want to delete workspace "${workspaceName}"?`)) {
      return
    }

    try {
      await apiClient.deleteWorkspace(workspaceId)
      toast({
        title: "Workspace deleted",
        description: `Workspace "${workspaceName}" deleted successfully`,
      })
      loadWorkspaces()
    } catch (error: any) {
      toast({
        title: "Error deleting workspace",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    }
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Workspaces</h1>
        <p className="text-muted-foreground">
          Manage your workspaces for organizing data and knowledge graphs
        </p>
      </div>

      {showCreateForm ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Create New Workspace</CardTitle>
            <CardDescription>Create a new workspace to organize your data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Workspace Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="My Workspace"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description (Optional)</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Workspace description"
                rows={3}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreate}>Create Workspace</Button>
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Button onClick={() => setShowCreateForm(true)} className="mb-6">
          <Plus className="h-4 w-4 mr-2" />
          Create Workspace
        </Button>
      )}

      {loading ? (
        <div className="text-center py-8 text-muted-foreground">Loading workspaces...</div>
      ) : workspaces.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FolderOpen className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="text-lg font-semibold mb-2">No workspaces</h3>
            <p className="text-muted-foreground mb-4">
              Create your first workspace to get started
            </p>
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Workspace
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workspaces.map((workspace) => (
            <Card key={workspace.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="mb-1">{workspace.name}</CardTitle>
                    <CardDescription className="text-xs">
                      ID: {workspace.id}
                    </CardDescription>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(workspace.id, workspace.name)}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {workspace.description && (
                  <p className="text-sm text-muted-foreground mb-4">
                    {workspace.description}
                  </p>
                )}
                <div className="flex gap-2">
                  <Link href={`/workspaces/${workspace.id}/files`}>
                    <Button variant="outline" size="sm" className="w-full">
                      View Files
                    </Button>
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
