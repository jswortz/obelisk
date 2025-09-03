import { useEffect, useState } from 'react'

interface ImageDisplayProps {
  src: string
  alt?: string
  className?: string
}

export function ImageDisplay({ src, alt, className }: ImageDisplayProps) {
  const [imageSrc, setImageSrc] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadImage = async () => {
      setLoading(true)
      
      // Check if it's already a data URL or regular URL
      if (src.startsWith('data:') || src.startsWith('http')) {
        setImageSrc(src)
        setLoading(false)
        return
      }

      // If it's an API path, fetch the image
      if (src.startsWith('/api/')) {
        try {
          const response = await fetch(src)
          const data = await response.json()
          
          // Check if response has inlineData
          if (data.inlineData?.data) {
            // Convert URL-safe base64 to standard base64
            const standardBase64 = data.inlineData.data
              .replace(/-/g, '+')
              .replace(/_/g, '/')
            
            // Add padding if needed
            const paddedBase64 = standardBase64 + '=='.substring(0, (4 - standardBase64.length % 4) % 4)
            
            setImageSrc(`data:${data.inlineData.mimeType || 'image/png'};base64,${paddedBase64}`)
          } else {
            // Fallback to original src if not inline data
            setImageSrc(src)
          }
        } catch (error) {
          console.error('Error loading image:', error)
          setImageSrc(src) // Fallback to original
        }
      } else {
        setImageSrc(src)
      }
      
      setLoading(false)
    }

    loadImage()
  }, [src])

  if (loading) {
    return (
      <div className={`${className} bg-muted animate-pulse flex items-center justify-center`}>
        <span className="text-muted-foreground">Loading...</span>
      </div>
    )
  }

  return <img src={imageSrc} alt={alt} className={className} />
}