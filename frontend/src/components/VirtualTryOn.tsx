import { useState } from 'react'
import { ImageUpload } from './ImageUpload'
import { ImageDisplay } from './ImageDisplay'
import { Button } from './ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Loader2 } from 'lucide-react'
import { useADKAPI } from '../hooks/useADKAPI'

interface VirtualTryOnProps {
  onComplete: (imageUrl: string, sessionId: string) => void
  sessionId: string | null
}

export function VirtualTryOn({ onComplete, sessionId }: VirtualTryOnProps) {
  const [personImage, setPersonImage] = useState<File | null>(null)
  const [productImage, setProductImage] = useState<File | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const { sendToAgent, loading, error, sessionId: currentSessionId } = useADKAPI(sessionId || undefined)

  const handleGenerate = async () => {
    if (!personImage || !productImage) return

    try {
      const message = "I have uploaded a person image and a product image. Please use load_artifacts to get these images, then use generate_virtual_try_on_images to create a virtual try-on with them."
      const data = await sendToAgent(message, {
        person: personImage,
        product: productImage
      })
      
      console.log('VirtualTryOn - data received:', data)
      console.log('VirtualTryOn - sessionId from response:', data.sessionId)
      
      setResult(data.image_url)
      if (data.image_url && data.sessionId) {
        console.log('VirtualTryOn - calling onComplete with:', data.image_url, data.sessionId)
        onComplete(data.image_url, data.sessionId)
      } else if (data.image_url) {
        console.error('VirtualTryOn - No session ID in response')
      }
    } catch (err) {
      // Error is already set by the hook
      console.error('Virtual try-on failed:', err)
    }
  }

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload Images</CardTitle>
            <CardDescription>
              Upload a person image and a product image to generate a virtual try-on
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <ImageUpload
              label="Person Image"
              value={personImage}
              onChange={setPersonImage}
            />
            
            <ImageUpload
              label="Product Image"
              value={productImage}
              onChange={setProductImage}
            />

            <Button
              className="w-full"
              onClick={handleGenerate}
              disabled={!personImage || !productImage || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                'Generate Virtual Try-On'
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
            <CardTitle>Result</CardTitle>
            <CardDescription>
              Your virtual try-on result will appear here
            </CardDescription>
          </CardHeader>
          <CardContent>
            {result ? (
              <ImageDisplay
                src={result}
                alt="Virtual try-on result"
                className="w-full rounded-lg"
              />
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