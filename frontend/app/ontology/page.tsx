'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, TrendingUp, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function OntologyPage() {
  const [entities, setEntities] = useState<string[]>([])
  const [relations, setRelations] = useState<string[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [entitiesResponse, relationsResponse, statsResponse] = await Promise.all([
        apiClient.getOntologyEntities().catch(() => ({ data: [] })),
        apiClient.getOntologyRelations().catch(() => ({ data: [] })),
        apiClient.getStats().catch(() => ({ data: null }))
      ])

      const entitiesData = entitiesResponse?.data || []
      const relationsData = relationsResponse?.data || []
      const statsData = statsResponse?.data || statsResponse || null

      setEntities(Array.isArray(entitiesData) ? entitiesData : [])
      setRelations(Array.isArray(relationsData) ? relationsData : [])
      setStats(statsData)
    } catch (err: any) {
      console.error('Error loading ontology data:', err)
      toast({
        title: "Error loading ontology",
        description: err.message || "Failed to fetch ontology data",
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

  const entityTypes = stats?.ontology?.entities ?? entities.length
  const relationTypes = stats?.ontology?.relations ?? relations.length

  return (
    <div className="p-8">
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Ontology Schema</h1>
            <p className="text-muted-foreground">
              Entity types and relation types defined in your ontology
            </p>
          </div>
          <Link href="/">
            <Button variant="outline">Back to Dashboard</Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 mb-8">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Entity Types</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{entityTypes}</div>
            <p className="text-xs text-muted-foreground">Defined in ontology</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Relation Types</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{relationTypes}</div>
            <p className="text-xs text-muted-foreground">Defined in ontology</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Entity Types</CardTitle>
            <CardDescription>All entity types in the ontology schema</CardDescription>
          </CardHeader>
          <CardContent>
            {entities.length > 0 ? (
              <div className="space-y-2">
                {entities.map((entity, index) => (
                  <div key={index} className="p-2 border rounded">
                    <span className="font-medium">{entity}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">No entity types defined yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Relation Types</CardTitle>
            <CardDescription>All relation types in the ontology schema</CardDescription>
          </CardHeader>
          <CardContent>
            {relations.length > 0 ? (
              <div className="space-y-2">
                {relations.map((relation, index) => (
                  <div key={index} className="p-2 border rounded">
                    <span className="font-medium">{relation}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">No relation types defined yet</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
