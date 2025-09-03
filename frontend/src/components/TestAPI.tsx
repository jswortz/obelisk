export function TestAPI() {
  const testAPI = async () => {
    try {
      const response = await fetch('/api')
      const data = await response.json()
      console.log('API Response:', data)
      alert(JSON.stringify(data))
    } catch (error) {
      console.error('API Error:', error)
      alert('Error: ' + error)
    }
  }

  return (
    <button onClick={testAPI} className="bg-blue-500 text-white px-4 py-2 rounded">
      Test API Connection
    </button>
  )
}