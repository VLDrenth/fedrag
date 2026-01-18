import ChatInterface from './components/ChatInterface'

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-blue-900 text-white py-4 px-6 shadow-md">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl font-bold">Fed RAG</h1>
          <p className="text-blue-200 text-sm">
            Ask questions about Federal Reserve communications
          </p>
        </div>
      </header>
      <main className="flex-1 max-w-4xl mx-auto w-full p-4">
        <ChatInterface />
      </main>
    </div>
  )
}

export default App
