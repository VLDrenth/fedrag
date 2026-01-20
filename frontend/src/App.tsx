import ChatInterface from './components/ChatInterface'

const documentTypes = [
  { name: 'Speeches', color: 'bg-violet-900/50' },
  { name: 'Statements', color: 'bg-blue-900/50' },
  { name: 'Minutes', color: 'bg-emerald-900/50' },
  { name: 'Testimony', color: 'bg-amber-900/50' },
];

function App() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Minimal header */}
      <header className="border-b border-white/10 bg-[#0a1628]/80 backdrop-blur-sm gradient-border">
        <div className="max-w-6xl mx-auto px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xl font-semibold tracking-tight text-white">
              fed<span className="text-blue-400">/</span>
            </span>
            <span className="text-stone-400 text-sm font-medium">research</span>
          </div>
        </div>
      </header>

      {/* Main content area with sidebar */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-3 md:px-6 py-4 md:py-6 flex gap-4 md:gap-6">
        {/* Sidebar - hidden on mobile */}
        <aside className="hidden md:block w-56 flex-shrink-0">
          <div className="bg-[#1a2942] rounded-xl border border-white/10 p-4">
            <h3 className="text-xs font-semibold text-stone-400 uppercase tracking-wider mb-4">
              Document Sources
            </h3>
            <ul className="space-y-2">
              {documentTypes.map((doc) => (
                <li key={doc.name} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${doc.color}`} />
                  <span className="text-sm text-stone-300">{doc.name}</span>
                </li>
              ))}
            </ul>
          </div>
        </aside>

        {/* Chat area */}
        <div className="flex-1 glass-card rounded-2xl shadow-2xl h-[calc(100dvh-80px)] md:h-[calc(100dvh-120px)] overflow-hidden border border-white/10">
          <ChatInterface />
        </div>
      </main>
    </div>
  )
}

export default App
