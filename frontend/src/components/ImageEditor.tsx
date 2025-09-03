import { useState } from 'react'
import { ImageDisplay } from './ImageDisplay'
import { Button } from './ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Label } from './ui/label'
import { Textarea } from './ui/textarea'
import { Loader2, Download } from 'lucide-react'
import { useADKAPI } from '../hooks/useADKAPI'

interface ImageEditorProps {
  initialImage: string | null
  sessionId: string | null
}

export function ImageEditor({ initialImage, sessionId }: ImageEditorProps) {
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const { sendToAgent, loading, error } = useADKAPI(sessionId || undefined)

  const handleRecontextualize = async () => {
    if (!initialImage || !prompt) return

    try {
      const message = `Please use the edit_image tool to recontextualize the virtual try-on image with this new background: "${prompt}". The last generated virtual try-on image should already be selected in your state.`
      const data = await sendToAgent(message)
      
      setResult(data.image_url)
    } catch (err) {
      // Error is already set by the hook
      console.error('Recontextualization failed:', err)
    }
  }

  const handleDownload = () => {
    if (result) {
      const link = document.createElement('a')
      link.href = result
      link.download = 'edited-image.png'
      link.click()
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Original Image</CardTitle>
            <CardDescription>
              The virtual try-on result from the previous step
            </CardDescription>
          </CardHeader>
          <CardContent>
            {initialImage ? (
              <ImageDisplay
                src={initialImage}
                alt="Original"
                className="w-full rounded-lg"
              />
            ) : (
              <div className="aspect-square bg-muted rounded-lg flex items-center justify-center">
                <p className="text-muted-foreground">No image available</p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Edit With Nano Banana 🍌</CardTitle>
            <CardDescription>
              Describe your edit!
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="prompt">Edit Prompt</Label>
              <Textarea
                id="prompt"
                placeholder="e.g., Place the person on top of Mt. Everest"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={4}
              />
            </div>

            <Button
              className="w-full"
              onClick={handleRecontextualize}
              disabled={!initialImage || !prompt || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                '🍌 Edit 🍌'
              )}
            </Button>

            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Edited Result</CardTitle>
            <CardDescription>
              Your recontextualized image will appear here
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result ? (
              <div className="space-y-4">
                <ImageDisplay
                  src={result}
                  alt="Edited result"
                  className="w-full rounded-lg"
                />
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={handleDownload}
                >
                  <Download className="mr-2 h-4 w-4" />
                  Download Image
                </Button>
              </div>
            ) : (
              <div className="aspect-square bg-muted rounded-lg flex items-center justify-center">
                <p className="text-muted-foreground">No result yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}