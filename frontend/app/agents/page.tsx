'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Search, Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function AgentsPage() {
  const [agents, setAgents] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getStats()
      const statsData = response?.data || response || null
      setAgents(statsData?.agents || {})
    } catch (err: any) {
      console.error('Error loading agents data:', err)
      toast({
        title: "Error loading agents",
        description: err.message || "Failed to fetch agents data",
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

  const agentList = agents ? Object.entries(agents) : []
  const activeAgents = agentList.filter(([_, agent]: [string, any]) => agent?.enabled !== false).length

  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Agents</h1>
            <p className="text-muted-foreground">
              Status and configuration of all system agents
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
            <CardTitle className="text-sm font-medium">Total Agents</CardTitle>
            <Search className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{agentList.length}</div>
            <p className="text-xs text-muted-foreground">All agents</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{activeAgents}</div>
            <p className="text-xs text-muted-foreground">Enabled agents</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6">
        {agentList.map(([key, agent]: [string, any]) => (
          <Card key={key}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {agent?.enabled !== false ? (
                      <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                      <XCircle className="h-5 w-5 text-gray-400" />
                    )}
                    {agent?.name || key}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </CardDescription>
                </div>
                <div className="text-sm">
                  <span className={`px-2 py-1 rounded ${
                    agent?.enabled !== false 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {agent?.enabled !== false ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {agent?.config && (
                <div className="space-y-2 text-sm">
                  <div className="grid gap-2 md:grid-cols-2">
                    {Object.entries(agent.config).map(([configKey, configValue]: [string, any]) => (
                      <div key={configKey} className="flex justify-between">
                        <span className="text-muted-foreground">{configKey}:</span>
                        <span className="font-medium">
                          {typeof configValue === 'object' 
                            ? JSON.stringify(configValue) 
                            : String(configValue)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
