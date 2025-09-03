import { useState } from 'react'
import { VirtualTryOn } from './components/VirtualTryOn'
import { ImageEditor } from './components/ImageEditor'
import { Button } from './components/ui/button'

type Mode = 'tryOn' | 'editor'

function App() {
  const [mode, setMode] = useState<Mode>('tryOn')
  const [tryOnImage, setTryOnImage] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)

  const handleTryOnComplete = (imageUrl: string, newSessionId: string) => {
    setTryOnImage(imageUrl)
    setSessionId(newSessionId)
    setMode('editor')
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold">Obelisk Virtual Try-On & Image Editor</h1>
          <div className="flex gap-2">
            <Button
              variant={mode === 'tryOn' ? 'default' : 'outline'}
              onClick={() => setMode('tryOn')}
            >
              Virtual Try-On
            </Button>
            <Button
              variant={mode === 'editor' ? 'default' : 'outline'}
              onClick={() => setMode('editor')}
              disabled={!tryOnImage}
            >
              Image Editor
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {mode === 'tryOn' ? (
          <VirtualTryOn onComplete={handleTryOnComplete} sessionId={sessionId} />
        ) : (
          <ImageEditor initialImage={tryOnImage} sessionId={sessionId} />
        )}
      </main>
    </div>
  )
}

export default App