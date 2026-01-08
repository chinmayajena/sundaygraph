'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  FolderOpen,
  FileText,
  Database,
  Search,
  Settings,
  Plus,
  ChevronRight,
  ChevronDown
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { apiClient } from '@/lib/api'

interface Workspace {
  id: string
  name: string
  description?: string
}

export function Sidebar() {
  const pathname = usePathname()
  const { toast } = useToast()
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<string | null>(null)
  const [expandedWorkspaces, setExpandedWorkspaces] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadWorkspaces()
    // Get selected workspace from localStorage
    const saved = localStorage.getItem('selectedWorkspace')
    if (saved) {
      setSelectedWorkspace(saved)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadWorkspaces = async () => {
    try {
      const result = await apiClient.getWorkspaces()
      setWorkspaces(result.data || [])
      if (result.data && result.data.length > 0 && !selectedWorkspace) {
        const first = result.data[0].id
        setSelectedWorkspace(first)
        localStorage.setItem('selectedWorkspace', first)
      }
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

  const toggleWorkspace = (workspaceId: string) => {
    const newExpanded = new Set(expandedWorkspaces)
    if (newExpanded.has(workspaceId)) {
      newExpanded.delete(workspaceId)
    } else {
      newExpanded.add(workspaceId)
    }
    setExpandedWorkspaces(newExpanded)
  }

  const handleCreateWorkspace = async () => {
    const name = prompt("Enter workspace name:")
    if (!name) return

    const id = name.toLowerCase().replace(/\s+/g, '-')
    try {
      await apiClient.createWorkspace({ workspace_id: id, name })
      toast({
        title: "Workspace created",
        description: `Workspace "${name}" created successfully`,
      })
      loadWorkspaces()
      setSelectedWorkspace(id)
      localStorage.setItem('selectedWorkspace', id)
    } catch (error: any) {
      toast({
        title: "Error creating workspace",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    }
  }

  const menuItems = [
    {
      title: 'Dashboard',
      icon: LayoutDashboard,
      href: '/',
      exact: true,
    },
    {
      title: 'Workspaces',
      icon: FolderOpen,
      href: '/workspaces',
    },
    {
      title: 'Graph',
      icon: Database,
      href: '/graph',
    },
    {
      title: 'Ontology',
      icon: Database,
      href: '/ontology',
    },
    {
      title: 'Files',
      icon: FileText,
      href: '/files',
    },
    {
      title: 'Agents',
      icon: Search,
      href: '/agents',
    },
    {
      title: 'Schema',
      icon: Database,
      href: selectedWorkspace ? `/workspaces/${selectedWorkspace}/schema` : '/schema',
      disabled: !selectedWorkspace,
    },
    {
      title: 'Query',
      icon: Search,
      href: selectedWorkspace ? `/workspaces/${selectedWorkspace}/query` : '/query',
      disabled: !selectedWorkspace,
    },
  ]

  return (
    <div className="flex flex-col h-full bg-background border-r">
      <div className="p-4 border-b">
        <h2 className="text-lg font-semibold mb-2">SundayGraph</h2>
        <Button
          onClick={handleCreateWorkspace}
          size="sm"
          className="w-full"
          variant="outline"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Workspace
        </Button>
      </div>

      <nav className="flex-1 overflow-y-auto p-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon
          const isActive = item.exact
            ? pathname === item.href
            : pathname?.startsWith(item.href || '')

          return (
            <Link
              key={item.href}
              href={item.disabled ? '#' : item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : item.disabled
                  ? "text-muted-foreground cursor-not-allowed opacity-50"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.title}
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t">
        <div className="text-xs font-medium text-muted-foreground mb-2">Workspaces</div>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {loading ? (
            <div className="text-xs text-muted-foreground">Loading...</div>
          ) : workspaces.length === 0 ? (
            <div className="text-xs text-muted-foreground">No workspaces</div>
          ) : (
            workspaces.map((workspace) => {
              const isExpanded = expandedWorkspaces.has(workspace.id)
              const isSelected = selectedWorkspace === workspace.id

              return (
                <div key={workspace.id}>
                  <button
                    onClick={() => {
                      setSelectedWorkspace(workspace.id)
                      localStorage.setItem('selectedWorkspace', workspace.id)
                      toggleWorkspace(workspace.id)
                    }}
                    className={cn(
                      "w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors",
                      isSelected
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:bg-accent"
                    )}
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    <span className="truncate">{workspace.name}</span>
                  </button>
                  {isExpanded && isSelected && (
                    <div className="ml-4 mt-1 space-y-1">
                      <Link
                        href={`/workspaces/${workspace.id}/files`}
                        className={cn(
                          "block px-2 py-1 rounded text-xs transition-colors",
                          pathname === `/workspaces/${workspace.id}/files`
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent"
                        )}
                      >
                        Files
                      </Link>
                      <Link
                        href={`/workspaces/${workspace.id}/schema`}
                        className={cn(
                          "block px-2 py-1 rounded text-xs transition-colors",
                          pathname === `/workspaces/${workspace.id}/schema`
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent"
                        )}
                      >
                        Schema
                      </Link>
                      <Link
                        href={`/workspaces/${workspace.id}/query`}
                        className={cn(
                          "block px-2 py-1 rounded text-xs transition-colors",
                          pathname === `/workspaces/${workspace.id}/query`
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent"
                        )}
                      >
                        Query
                      </Link>
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
