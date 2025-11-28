"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

// Types pour les modèles
interface ModelInfo {
  id: string
  name: string
  params?: string
  ram?: string
  speed?: string
  quality?: string
  cost?: string
  context?: string
  best_for?: string
  recommended?: boolean
  test_score?: string
  issues?: string
  requires_gpu?: boolean
  quantization?: string
}

interface ProviderInfo {
  name: string
  description: string
  icon: string
  requires_api_key: boolean
  requires_mlx_server?: boolean
  requires_gpu?: boolean
  server_url?: string
  default: string
  models: ModelInfo[]
}

interface ModelsResponse {
  providers: Record<string, ProviderInfo>
  defaults: {
    model_id: string
    extraction_method: string
  }
}

interface ExtractionMethod {
  name: string
  description: string
  speed: string
  quality: string
  supports_ocr: boolean
  supports_tables: boolean
  recommended_for: string
  available: boolean
}

interface ExtractionMethodsResponse {
  methods: Record<string, ExtractionMethod>
  docling_available: boolean
  default: string
}

interface AdvancedSettingsProps {
  onSettingsChange?: (settings: AnalysisSettings) => void
  initialSettings?: AnalysisSettings
  className?: string
}

export interface AnalysisSettings {
  model_id: string
  extraction_method: string
  use_ocr: boolean
}

// Utiliser des URLs relatives pour passer par le proxy Next.js
const API_BASE_URL = ""

// Icones simples en SVG
const Icons = {
  server: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2" />
    </svg>
  ),
  cloud: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 15a4 4 0 004 4h9a5 5 0 10-.1-9.999 5.002 5.002 0 10-9.78 2.096A4.001 4.001 0 003 15z" />
    </svg>
  ),
  cpu: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
    </svg>
  ),
  box: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  ),
  chevronDown: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  ),
  chevronUp: (
    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  ),
  settings: (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  ),
}

const iconMap: Record<string, React.ReactNode> = {
  server: Icons.server,
  cloud: Icons.cloud,
  cpu: Icons.cpu,
  box: Icons.box,
}

export function AdvancedSettings({
  onSettingsChange,
  initialSettings,
  className,
}: AdvancedSettingsProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Données des modèles
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({})
  const [extractionMethods, setExtractionMethods] = useState<Record<string, ExtractionMethod>>({})
  const [doclingAvailable, setDoclingAvailable] = useState(false)

  // Settings actuels
  const [activeProvider, setActiveProvider] = useState("ollama")
  const [selectedModel, setSelectedModel] = useState(initialSettings?.model_id || "")
  const [extractionMethod, setExtractionMethod] = useState(initialSettings?.extraction_method || "pypdf")
  const [useOcr, setUseOcr] = useState(initialSettings?.use_ocr || false)

  // Charger les données au montage
  useEffect(() => {
    loadModels()
    loadExtractionMethods()
  }, [])

  // Notifier les changements
  useEffect(() => {
    if (onSettingsChange && selectedModel) {
      onSettingsChange({
        model_id: selectedModel,
        extraction_method: extractionMethod,
        use_ocr: useOcr,
      })
    }
  }, [selectedModel, extractionMethod, useOcr, onSettingsChange])

  const loadModels = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings/models`)
      if (!response.ok) throw new Error("Failed to load models")
      const data: ModelsResponse = await response.json()
      setProviders(data.providers)
      if (!selectedModel && data.defaults.model_id) {
        setSelectedModel(data.defaults.model_id)
        // Déterminer le provider actif
        const provider = data.defaults.model_id.split(":")[0]
        setActiveProvider(provider)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement")
    } finally {
      setIsLoading(false)
    }
  }

  const loadExtractionMethods = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/settings/extraction-methods`)
      if (!response.ok) throw new Error("Failed to load extraction methods")
      const data: ExtractionMethodsResponse = await response.json()
      setExtractionMethods(data.methods)
      setDoclingAvailable(data.docling_available)
      if (!extractionMethod && data.default) {
        setExtractionMethod(data.default)
      }
    } catch (err) {
      console.error("Failed to load extraction methods:", err)
    }
  }

  const handleProviderChange = (provider: string) => {
    setActiveProvider(provider)
    // Sélectionner le modèle par défaut du provider
    const providerInfo = providers[provider]
    if (providerInfo?.default) {
      setSelectedModel(providerInfo.default)
    } else if (providerInfo?.models?.[0]) {
      setSelectedModel(providerInfo.models[0].id)
    }
  }

  const handleModelChange = (value: string) => {
    setSelectedModel(value)
  }

  const getSelectedModelInfo = (): ModelInfo | undefined => {
    const provider = providers[activeProvider]
    return provider?.models?.find((m) => m.id === selectedModel)
  }

  const modelInfo = getSelectedModelInfo()

  return (
    <div className={cn("w-full", className)}>
      {/* Header avec toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-full flex items-center justify-between p-4 rounded-lg",
          "bg-muted/50 hover:bg-muted transition-colors",
          "border border-border",
          isOpen && "rounded-b-none border-b-0"
        )}
      >
        <div className="flex items-center gap-3">
          {Icons.settings}
          <div className="text-left">
            <h3 className="font-medium">Paramètres avancés</h3>
            <p className="text-sm text-muted-foreground">
              {selectedModel ? (
                <>Modèle: {modelInfo?.name || selectedModel}</>
              ) : (
                "Configurer le modèle LLM et l'extraction"
              )}
            </p>
          </div>
        </div>
        {isOpen ? Icons.chevronUp : Icons.chevronDown}
      </button>

      {/* Contenu */}
      {isOpen && (
        <Card className="rounded-t-none border-t-0">
          <CardContent className="p-6 space-y-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              </div>
            ) : error ? (
              <div className="text-destructive text-center py-4">{error}</div>
            ) : (
              <>
                {/* Section Modèle LLM */}
                <div className="space-y-4">
                  <h4 className="font-medium">Modèle LLM</h4>

                  {/* Tabs pour les providers */}
                  <Tabs value={activeProvider} onValueChange={handleProviderChange}>
                    <TabsList className="w-full grid grid-cols-4 gap-1">
                      {Object.entries(providers).map(([key, provider]) => (
                        <TabsTrigger
                          key={key}
                          value={key}
                          className="flex items-center gap-2 text-xs"
                        >
                          {iconMap[provider.icon]}
                          <span className="hidden sm:inline">{provider.name}</span>
                        </TabsTrigger>
                      ))}
                    </TabsList>

                    {Object.entries(providers).map(([key, provider]) => (
                      <TabsContent key={key} value={key} className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                          {provider.description}
                        </p>

                        {/* Avertissements */}
                        {provider.requires_api_key && (
                          <div className="text-sm text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-400 p-3 rounded-md">
                            Nécessite une clé API Anthropic
                          </div>
                        )}
                        {provider.requires_mlx_server && (
                          <div className="text-sm text-blue-600 bg-blue-50 dark:bg-blue-950 dark:text-blue-400 p-3 rounded-md">
                            Nécessite un serveur MLX sur {provider.server_url}
                          </div>
                        )}
                        {provider.requires_gpu && (
                          <div className="text-sm text-purple-600 bg-purple-50 dark:bg-purple-950 dark:text-purple-400 p-3 rounded-md">
                            GPU recommande pour de meilleures performances
                          </div>
                        )}

                        {/* Select du modele */}
                        <div className="space-y-2">
                          <Label>Sélectionner un modèle</Label>
                          <Select value={selectedModel} onValueChange={handleModelChange}>
                            <SelectTrigger>
                              <SelectValue placeholder="Sélectionner un modèle" />
                            </SelectTrigger>
                            <SelectContent>
                              {provider.models?.map((model) => (
                                <SelectItem key={model.id} value={model.id}>
                                  {model.name}
                                  {model.recommended && " ⭐"}
                                  {model.test_score && ` (${model.test_score})`}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Info du modele selectionne */}
                        {modelInfo && (
                          <div className="bg-muted/50 p-4 rounded-md space-y-2">
                            <div className="flex flex-wrap gap-2">
                              {modelInfo.recommended && (
                                <Badge variant="default">Recommandé</Badge>
                              )}
                              {modelInfo.quality && (
                                <Badge variant="secondary">
                                  Qualité: {modelInfo.quality}
                                </Badge>
                              )}
                              {modelInfo.speed && (
                                <Badge variant="outline">
                                  Vitesse: {modelInfo.speed}
                                </Badge>
                              )}
                              {modelInfo.ram && (
                                <Badge variant="outline">RAM: {modelInfo.ram}</Badge>
                              )}
                              {modelInfo.test_score && (
                                <Badge variant="secondary">
                                  Score test: {modelInfo.test_score}
                                </Badge>
                              )}
                            </div>
                            {modelInfo.best_for && (
                              <p className="text-sm text-muted-foreground">
                                {modelInfo.best_for}
                              </p>
                            )}
                            {modelInfo.cost && (
                              <p className="text-sm text-muted-foreground">
                                Cout: {modelInfo.cost}
                              </p>
                            )}
                            {modelInfo.issues && (
                              <p className="text-sm text-destructive">
                                {modelInfo.issues}
                              </p>
                            )}
                          </div>
                        )}
                      </TabsContent>
                    ))}
                  </Tabs>
                </div>

                {/* Separateur */}
                <div className="border-t border-border" />

                {/* Section Extraction PDF */}
                <div className="space-y-4">
                  <h4 className="font-medium">Extraction PDF</h4>

                  <div className="space-y-2">
                    <Label>Méthode d'extraction</Label>
                    <Select value={extractionMethod} onValueChange={setExtractionMethod}>
                      <SelectTrigger>
                        <SelectValue placeholder="Sélectionner une méthode" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(extractionMethods).map(([key, method]) => (
                          <SelectItem key={key} value={key} disabled={!method.available}>
                            {method.name}
                            {!method.available && " (non installé)"}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {extractionMethods[extractionMethod] && (
                    <div className="bg-muted/50 p-4 rounded-md space-y-2">
                      <p className="text-sm">
                        {extractionMethods[extractionMethod].description}
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Badge variant="outline">
                          Vitesse: {extractionMethods[extractionMethod].speed}
                        </Badge>
                        <Badge variant="outline">
                          Qualité: {extractionMethods[extractionMethod].quality}
                        </Badge>
                        {extractionMethods[extractionMethod].supports_ocr && (
                          <Badge variant="secondary">OCR</Badge>
                        )}
                        {extractionMethods[extractionMethod].supports_tables && (
                          <Badge variant="secondary">Tableaux</Badge>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Toggle OCR (si supporte) */}
                  {extractionMethods[extractionMethod]?.supports_ocr && (
                    <div className="flex items-center justify-between">
                      <div>
                        <Label className="text-sm">Activer l'OCR</Label>
                        <p className="text-xs text-muted-foreground">
                          Pour les PDFs scannés ou images
                        </p>
                      </div>
                      <Switch
                        checked={useOcr}
                        onCheckedChange={setUseOcr}
                      />
                    </div>
                  )}

                  {!doclingAvailable && extractionMethod.startsWith("docling") && (
                    <div className="text-sm text-amber-600 bg-amber-50 dark:bg-amber-950 dark:text-amber-400 p-3 rounded-md">
                      Docling n'est pas installé. Installer avec:{" "}
                      <code className="bg-amber-100 dark:bg-amber-900 px-1 rounded">
                        uv sync --extra docling
                      </code>
                    </div>
                  )}
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

export default AdvancedSettings
