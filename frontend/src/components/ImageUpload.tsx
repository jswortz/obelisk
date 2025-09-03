import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from './ui/button'

interface ImageUploadProps {
  label: string
  value: File | null
  onChange: (file: File | null) => void
  accept?: Record<string, string[]>
}

export function ImageUpload({ label, value, onChange, accept = { 'image/*': [] } }: ImageUploadProps) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onChange(acceptedFiles[0])
    }
  }, [onChange])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxFiles: 1,
    maxSize: 30 * 1024 * 1024, // 30MB
  })

  const imageUrl = value ? URL.createObjectURL(value) : null

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium">{label}</label>
      
      {!value ? (
        <div
          {...getRootProps()}
          className={cn(
            "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors",
            isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
          )}
        >
          <input {...getInputProps()} />
          <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground">
            {isDragActive ? "Drop the image here..." : "Drag & drop an image here, or click to select"}
          </p>
          <p className="text-xs text-muted-foreground mt-2">Max file size: 30MB</p>
        </div>
      ) : (
        <div className="relative">
          <img
            src={imageUrl}
            alt={label}
            className="w-full h-64 object-cover rounded-lg"
          />
          <Button
            size="icon"
            variant="destructive"
            className="absolute top-2 right-2"
            onClick={() => onChange(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}