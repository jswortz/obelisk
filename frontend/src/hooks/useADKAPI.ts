import { useState, useRef, useEffect } from 'react'

const USER_ID = 'u_999'
const APP_NAME = 'obelisk_recontext_agent'

export function useADKAPI(sharedSessionId?: string) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(sharedSessionId || null)
  const sessionIdRef = useRef<string | null>(sharedSessionId || null)
  
  // Update session ID if shared one changes
  useEffect(() => {
    if (sharedSessionId) {
      sessionIdRef.current = sharedSessionId
      setSessionId(sharedSessionId)
    }
  }, [sharedSessionId])

  const createSession = async () => {
    const sessionId = `session-${Date.now()}`
    const response = await fetch(`/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionId}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })
    
    if (!response.ok) {
      throw new Error(`Failed to create session: ${response.status}`)
    }
    
    sessionIdRef.current = sessionId
    setSessionId(sessionId)
    return sessionId
  }

  const uploadArtifact = async (file: File, name: string) => {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await fetch(`/api/artifacts/upload?name=${name}`, {
      method: 'POST',
      body: formData
    })
    
    if (!response.ok) {
      throw new Error(`Failed to upload artifact: ${response.status}`)
    }
    
    const result = await response.json()
    return result.uri || result.url || result.path
  }

  const sendToAgent = async (message: string, files?: { person?: File; product?: File }) => {
    setLoading(true)
    setError(null)

    try {
      // Create session if needed
      if (!sessionIdRef.current) {
        console.log('Creating new session...')
        await createSession()
        console.log('Session created:', sessionIdRef.current)
      }
      
      // Send images as inline data with the message
      const parts: any[] = [{ text: message }]
      
      if (files?.person) {
        console.log('Adding person image to message...')
        const personData = await fileToBase64(files.person)
        parts.push({
          inlineData: {
            data: personData,
            mimeType: files.person.type || 'image/png'
          }
        })
      }
      
      if (files?.product) {
        console.log('Adding product image to message...')
        const productData = await fileToBase64(files.product)
        parts.push({
          inlineData: {
            data: productData,
            mimeType: files.product.type || 'image/png'
          }
        })
      }

      const payload = {
        appName: APP_NAME,
        userId: USER_ID,
        sessionId: sessionIdRef.current,
        newMessage: {
          parts,
          role: 'user'
        },
        streaming: false
      }
      
      console.log('Sending to ADK:', payload)
      
      const response = await fetch('/api/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      })
      
      console.log('Response status:', response.status)

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const events = await response.json()
      console.log('ADK Response:', events)
      
      // Try different response formats
      for (const event of events) {
        console.log('Processing event:', event)
        
        // Check for tool_responses in the event
        if (event.tool_responses) {
          console.log('Found tool_responses:', event.tool_responses)
          for (const toolResponse of event.tool_responses) {
            if (toolResponse.response) {
              // Check if it's an edit_image response
              if (toolResponse.response.status === 'complete' && toolResponse.response.image_filenames) {
                const filename = toolResponse.response.image_filenames[0]
                console.log('Found edited image filename:', filename)
                const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${filename}`
                return { image_url: artifactUrl, sessionId: sessionIdRef.current }
              }
            }
          }
        }
        
        // Check content.parts for text
        if (event.content?.parts) {
          console.log('Found content parts:', event.content.parts)
          for (const part of event.content.parts) {
            if (part.text) {
              console.log('Part text:', part.text)
            }
          }
        }
        
        // Check actions for artifacts
        if (event.actions?.artifactDelta) {
          console.log('Found artifactDelta:', event.actions.artifactDelta)
          // Store artifact IDs for follow-up
          const artifactIds = Object.keys(event.actions.artifactDelta)
          
          // Handle single artifact (e.g., from edit_image)
          if (artifactIds.length === 1) {
            console.log('Found single artifact:', artifactIds[0])
            const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${artifactIds[0]}`
            return { image_url: artifactUrl, sessionId: sessionIdRef.current }
          }
          
          if (artifactIds.length === 2) {
            // We have both artifacts, now send follow-up to generate virtual try-on
            console.log('Artifacts created, sending follow-up message...')
            
            const followUpPayload = {
              appName: APP_NAME,
              userId: USER_ID,
              sessionId: sessionIdRef.current,
              newMessage: {
                parts: [{
                  text: `Now please use the generate_virtual_try_on_images tool to create a virtual try-on using these two artifacts. The first artifact (${artifactIds[0]}) is the person image and the second (${artifactIds[1]}) is the product image.`
                }],
                role: 'user'
              },
              streaming: false
            }
            
            const followUpResponse = await fetch('/api/run', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify(followUpPayload)
            })
            
            if (followUpResponse.ok) {
              const followUpEvents = await followUpResponse.json()
              console.log('Follow-up response:', followUpEvents)
              
              // Process follow-up response for virtual try-on result
              for (const followUpEvent of followUpEvents) {
                // Check for generated images in artifacts
                if (followUpEvent.actions?.artifactDelta) {
                  const newArtifacts = Object.keys(followUpEvent.actions.artifactDelta)
                  // Find the new artifact (not one of the original two)
                  const resultArtifact = newArtifacts.find(id => !artifactIds.includes(id))
                  if (resultArtifact) {
                    console.log('Found result artifact:', resultArtifact)
                    const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${resultArtifact}`
                    return { image_url: artifactUrl, sessionId: sessionIdRef.current }
                  }
                }
                
                // Check for text content with artifact references
                if (followUpEvent.content?.parts) {
                  for (const part of followUpEvent.content.parts) {
                    if (part.text) {
                      // Look for artifact references in text
                      const artifactMatch = part.text.match(/([a-f0-9-]{36}\.png)/i)
                      if (artifactMatch && !artifactIds.includes(artifactMatch[1])) {
                        console.log('Found artifact in text:', artifactMatch[1])
                        const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${artifactMatch[1]}`
                        return { image_url: artifactUrl, sessionId: sessionIdRef.current }
                      }
                    }
                  }
                }
              }
            }
          }
        }
        // Check for tool calls
        if (event.tool_calls) {
          console.log('Found tool_calls:', event.tool_calls)
          for (const toolCall of event.tool_calls) {
            if (toolCall.function_response?.response) {
              const response = toolCall.function_response.response
              // Check for edit_image response format
              if (response.status === 'complete' && response.image_filenames) {
                const filename = response.image_filenames[0]
                console.log('Found edited image in tool_calls:', filename)
                const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${filename}`
                return { image_url: artifactUrl, sessionId: sessionIdRef.current }
              }
              // Check for array of URLs
              if (Array.isArray(response) && response.length > 0) {
                return { image_url: response[0], sessionId: sessionIdRef.current }
              }
            }
          }
        }
        
        // Check for toolCalls (camelCase)
        if (event.toolCalls) {
          console.log('Found toolCalls:', event.toolCalls)
          for (const toolCall of event.toolCalls) {
            if (toolCall.functionResponse?.response) {
              const response = toolCall.functionResponse.response
              // Check for edit_image response format
              if (response.status === 'complete' && response.image_filenames) {
                const filename = response.image_filenames[0]
                console.log('Found edited image in toolCalls:', filename)
                const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${filename}`
                return { image_url: artifactUrl, sessionId: sessionIdRef.current }
              }
              // Check for array of URLs
              if (Array.isArray(response) && response.length > 0) {
                return { image_url: response[0], sessionId: sessionIdRef.current }
              }
            }
          }
        }
        
        // Check for server events/artifacts
        if (event.server_events?.artifacts) {
          console.log('Found artifacts:', event.server_events.artifacts)
          const artifacts = event.server_events.artifacts
          if (artifacts.length > 0) {
            const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${artifacts[0].uri}`
            return { image_url: artifactUrl, sessionId: sessionIdRef.current }
          }
        }
        
        // Check for text content with image URLs or artifact references
        if (event.text) {
          console.log('Found text:', event.text)
          // Look for URLs in text
          const urlMatch = event.text.match(/https?:\/\/[^\s]+\.(jpg|jpeg|png|gif|webp)/i)
          if (urlMatch) {
            return { image_url: urlMatch[0], sessionId: sessionIdRef.current }
          }
          
          // Look for artifact references in text
          const artifactMatch = event.text.match(/([a-f0-9-]{36}\.png)/i)
          if (artifactMatch) {
            console.log('Found artifact in text:', artifactMatch[1])
            const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${artifactMatch[1]}`
            return { image_url: artifactUrl, sessionId: sessionIdRef.current }
          }
        }
        
        // Check content.parts for text with artifact references
        if (event.content?.parts) {
          for (const part of event.content.parts) {
            if (part.text) {
              const artifactMatch = part.text.match(/([a-f0-9-]{36}\.png)/i)
              if (artifactMatch) {
                console.log('Found artifact in content:', artifactMatch[1])
                const artifactUrl = `/api/apps/${APP_NAME}/users/${USER_ID}/sessions/${sessionIdRef.current}/artifacts/${artifactMatch[1]}`
                return { image_url: artifactUrl, sessionId: sessionIdRef.current }
              }
            }
          }
        }
      }

      throw new Error('No image generated')
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An error occurred'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { sendToAgent, loading, error, sessionId }
}

async function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const dataUrl = e.target?.result as string
      // Remove the data URL prefix to get just base64
      const base64 = dataUrl.split(',')[1]
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}