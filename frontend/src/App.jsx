import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import InputBox from "./components/InputBox";
import AudioRecorder from "./components/AudioRecorder";
import ImageUpload from "./components/ImageUpload";
import ResultCard from "./components/ResultCard";
import { streamFactCheck } from "./services/api";

function App() {
  const [query, setQuery] = useState("");
  const [response, setResponse] = useState("");
  const [meta, setMeta] = useState(null);
  const [mode, setMode] = useState("rag");
  const [loading, setLoading] = useState(false);
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark' || 
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
    return false;
  });
  const scrollRef = useRef(null);

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [dark]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [response]);

  const handleSubmit = async () => {
    if (!query.trim()) return;

    setResponse("");
    setMeta(null);
    setLoading(true);

    try {
      await streamFactCheck(query, mode, (chunk) => {
        if (chunk.type === "text") {
          setResponse((prev) => prev + chunk.data);
        } else if (chunk.type === "meta") {
          setMeta(chunk.data);
          setLoading(false);
        }
      });
    } catch (error) {
      console.error("Fact check failed:", error);
      setLoading(false);
      setResponse("An error occurred during verification. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors duration-500 selection:bg-brand/30">
      
      {/* BACKGROUND DECORATION */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-brand/5 dark:bg-brand/10 rounded-full blur-[120px] animate-pulse" />
        <div className="absolute top-[20%] -right-[5%] w-[30%] h-[30%] bg-blue-500/5 dark:bg-blue-500/10 rounded-full blur-[100px] animate-pulse [animation-delay:1s]" />
      </div>

      {/* NAVBAR */}
      <header className="sticky top-0 z-50 glass-panel border-b-0 backdrop-blur-md px-6 py-4">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2 group cursor-pointer"
          >
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-brand/20 group-hover:rotate-12 transition-transform">
              L
            </div>
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-brand to-brand-dark bg-clip-text text-transparent">
              Fact Lens
            </h1>
          </motion.div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex bg-slate-200/50 dark:bg-slate-800/50 p-1 rounded-full text-xs font-medium border border-slate-200/50 dark:border-slate-700/50">
              <button
                onClick={() => setMode("rag")}
                className={`px-4 py-1.5 rounded-full transition-all duration-300 ${mode === 'rag' ? 'bg-white dark:bg-slate-700 shadow-md text-brand scale-105' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
              >
                RAG Mode
              </button>
              <button
                onClick={() => setMode("no_rag")}
                className={`px-4 py-1.5 rounded-full transition-all duration-300 ${mode === 'no_rag' ? 'bg-white dark:bg-slate-700 shadow-md text-brand scale-105' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
              >
                Fast Mode
              </button>
            </div>
            <button
              onClick={() => setDark(!dark)}
              className="theme-toggle-btn group relative overflow-hidden"
              aria-label="Toggle Theme"
            >
              <motion.div
                initial={false}
                animate={{ y: dark ? 40 : 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="absolute"
              >
                🌙
              </motion.div>
              <motion.div
                initial={false}
                animate={{ y: dark ? 0 : -40 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className="absolute"
              >
                ☀️
              </motion.div>
            </button>
          </div>
        </div>
      </header>

      <main className="relative max-w-4xl mx-auto px-6 py-12">
        {/* HERO SECTION */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <span className="inline-block px-4 py-1 bg-brand/10 text-brand text-[10px] font-bold rounded-full mb-4 tracking-widest uppercase border border-brand/20 animate-pulse-soft">
            AI-Powered Verification
          </span>
          <h2 className="text-4xl sm:text-5xl font-extrabold mb-4 tracking-tight">
            Verify Claims in <span className="text-brand hover-glow">Real-Time</span>
          </h2>
          <p className="text-slate-500 dark:text-slate-400 max-w-xl mx-auto text-lg leading-relaxed">
            Cross-reference information across global news and databases instantly with state-of-the-art AI.
          </p>
        </motion.div>

        {/* INPUT COMPONENT */}
        <section className="glass-panel p-2 rounded-3xl mb-8 group focus-within:ring-2 focus-within:ring-brand/30 transition-all duration-500 interactive-card">
          <div className="flex flex-col gap-2">
            <div className="relative">
              <InputBox 
                query={query} 
                setQuery={setQuery} 
                onSubmit={handleSubmit}
                placeholder="Paste a claim, article link, or ask a question..."
              />
            </div>
            
            <div className="flex items-center justify-between p-3">
              <div className="flex items-center gap-2">
                <AudioRecorder setQuery={setQuery} />
                <ImageUpload />
                <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-1" />
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter hidden sm:inline">
                  {mode === 'rag' ? 'Comprehensive search active' : 'Direct verification active'}
                </span>
              </div>
              
              <button
                onClick={handleSubmit}
                disabled={loading || !query.trim()}
                className={`
                  flex items-center gap-2 px-8 py-3 rounded-2xl font-bold transition-all duration-300 shadow-xl
                  ${loading || !query.trim() 
                    ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed shadow-none' 
                    : 'bg-brand hover:bg-brand-dark text-white hover:scale-105 active:scale-95 shadow-brand/30 hover:shadow-brand/40'}
                `}
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    <span>Verify Now</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </section>

        {/* RESULTS SECTION */}
        <AnimatePresence mode="wait">
          {(response || loading) && (
            <motion.div
              initial={{ opacity: 0, y: 30, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ type: "spring", stiffness: 200, damping: 20 }}
              className="glass-panel rounded-3xl overflow-hidden interactive-card"
            >
              <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/20">
                <h3 className="font-bold text-lg flex items-center gap-2">
                  <span className="w-2 h-2 bg-brand rounded-full animate-pulse" />
                  Verification Report
                </h3>
                {meta && (
                  <motion.div 
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border ${
                      parseFloat(meta.confidence) > 0.7 
                      ? 'bg-green-100/50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800' 
                      : 'bg-amber-100/50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800'
                    }`}
                  >
                    {Math.round(parseFloat(meta.confidence) * 100)}% Confidence
                  </motion.div>
                )}
              </div>

              <div 
                ref={scrollRef}
                className="p-8 max-h-[600px] overflow-y-auto leading-relaxed text-slate-700 dark:text-slate-300"
              >
                {loading && !response && (
                  <div className="flex flex-col items-center justify-center py-16 gap-6">
                    <div className="relative">
                      <div className="w-16 h-16 border-4 border-brand/10 border-t-brand rounded-full animate-spin" />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-8 h-8 bg-brand/10 rounded-full animate-pulse" />
                      </div>
                    </div>
                    <div className="text-center">
                      <p className="text-sm font-bold uppercase tracking-widest animate-pulse-soft">Scanning Global Data</p>
                      <p className="text-xs text-slate-400 mt-2">Checking news, databases, and cross-referencing...</p>
                    </div>
                  </div>
                )}
                
                <div className="prose dark:prose-invert max-w-none prose-p:my-4 prose-p:leading-loose text-lg">
                  {response}
                  {loading && response && (
                    <span className="inline-block w-2 h-6 bg-brand ml-2 animate-pulse" />
                  )}
                </div>

                {meta && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <ResultCard meta={meta} />
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* FOOTER */}
      <footer className="py-12 text-center text-slate-400 text-[10px] font-bold uppercase tracking-[0.2em]">
        <p>© 2026 Fact Lens • The Truth Decoded</p>
      </footer>
    </div>
  );
}

export default App;
