'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Database, TrendingUp, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function GraphPage() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getStats()
      const statsData = response?.data || response || null
      setStats(statsData)
    } catch (err: any) {
      console.error('Error loading graph data:', err)
      toast({
        title: "Error loading graph data",
        description: err.message || "Failed to fetch graph statistics",
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

  const graphNodes = stats?.graph?.nodes ?? 0
  const graphEdges = stats?.graph?.edges ?? 0
  const entityTypes = stats?.graph?.entity_types ?? 0
  const relationTypes = stats?.graph?.relation_types ?? 0

  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Knowledge Graph</h1>
            <p className="text-muted-foreground">
              Detailed view of your knowledge graph structure
            </p>
          </div>
          <Link href="/">
            <Button variant="outline">Back to Dashboard</Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Nodes</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{graphNodes}</div>
            <p className="text-xs text-muted-foreground">Entities in graph</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Edges</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{graphEdges}</div>
            <p className="text-xs text-muted-foreground">Relationships</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Entity Types</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{entityTypes}</div>
            <p className="text-xs text-muted-foreground">Unique types</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Relation Types</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{relationTypes}</div>
            <p className="text-xs text-muted-foreground">Unique types</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Graph Details</CardTitle>
          <CardDescription>Complete graph statistics and information</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h3 className="font-semibold mb-2">Graph Structure</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Nodes:</span>
                    <span className="font-medium">{graphNodes}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Edges:</span>
                    <span className="font-medium">{graphEdges}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Density:</span>
                    <span className="font-medium">
                      {graphNodes > 0 ? (graphEdges / (graphNodes * (graphNodes - 1))).toFixed(4) : '0.0000'}
                    </span>
                  </div>
                </div>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Type Distribution</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Entity Types:</span>
                    <span className="font-medium">{entityTypes}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Relation Types:</span>
                    <span className="font-medium">{relationTypes}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
