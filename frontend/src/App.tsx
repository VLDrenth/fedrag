import ChatInterface from './components/ChatInterface'

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Minimal header */}
      <header className="border-b border-white/10 bg-[#0a1628]/80 backdrop-blur-sm gradient-border">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xl font-semibold tracking-tight text-white">
              fed<span className="text-blue-400">/</span>
            </span>
            <span className="text-stone-400 text-sm font-medium">research</span>
          </div>
        </div>
      </header>

      {/* Main content area */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-6">
        <div className="glass-card rounded-2xl shadow-2xl h-[calc(100vh-120px)] overflow-hidden border border-white/10">
          <ChatInterface />
        </div>
      </main>
    </div>
  )
}

export default App
