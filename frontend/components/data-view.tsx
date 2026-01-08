'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Search, RefreshCw, Database, Network } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

export function DataView() {
  const [query, setQuery] = useState('')
  const [queryType, setQueryType] = useState('entity')
  const [results, setResults] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()

  const loadStats = async () => {
    try {
      const result = await apiClient.getStats()
      setStats(result.data)
    } catch (error: any) {
      toast({
        title: "Error loading stats",
        description: error.message,
        variant: "destructive",
      })
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  const handleQuery = async () => {
    if (!query.trim()) {
      toast({
        title: "Error",
        description: "Please enter a query",
        variant: "destructive",
      })
      return
    }

    setLoading(true)
    try {
      const result = await apiClient.query({ query, query_type: queryType })
      setResults(result.data || [])
      toast({
        title: "Query executed",
        description: `Found ${result.data?.length || 0} results`,
      })
    } catch (error: any) {
      toast({
        title: "Query failed",
        description: error.response?.data?.detail || error.message,
        variant: "destructive",
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Query Knowledge Graph</CardTitle>
              <CardDescription>Search and explore your knowledge graph</CardDescription>
            </div>
            <Button variant="outline" size="sm" onClick={loadStats}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <div className="flex-1 space-y-2">
              <Label htmlFor="query">Query</Label>
              <Input
                id="query"
                placeholder="Enter your query..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
              />
            </div>
            <div className="w-40 space-y-2">
              <Label htmlFor="type">Type</Label>
              <select
                id="type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={queryType}
                onChange={(e) => setQueryType(e.target.value)}
              >
                <option value="entity">Entity</option>
                <option value="relation">Relation</option>
                <option value="neighbor">Neighbor</option>
                <option value="path">Path</option>
              </select>
            </div>
            <div className="flex items-end">
              <Button onClick={handleQuery} disabled={loading}>
                <Search className="h-4 w-4 mr-2" />
                Search
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Graph Statistics
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats ? (
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Nodes:</span>
                  <span className="font-semibold">{stats.graph?.nodes || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Edges:</span>
                  <span className="font-semibold">{stats.graph?.edges || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Entity Types:</span>
                  <span className="font-semibold">{stats.ontology?.entities || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Relation Types:</span>
                  <span className="font-semibold">{stats.ontology?.relations || 0}</span>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">Loading statistics...</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Network className="h-5 w-5" />
              Query Results
            </CardTitle>
          </CardHeader>
          <CardContent>
            {results.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {results.slice(0, 10).map((result, idx) => (
                  <div key={idx} className="p-3 border rounded-lg text-sm">
                    <pre className="whitespace-pre-wrap text-xs">
                      {JSON.stringify(result, null, 2)}
                    </pre>
                  </div>
                ))}
                {results.length > 10 && (
                  <p className="text-sm text-muted-foreground text-center">
                    Showing 10 of {results.length} results
                  </p>
                )}
              </div>
            ) : (
              <p className="text-muted-foreground">No results yet. Run a query to see results.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

