import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import InputBox from "./components/InputBox";
import AudioRecorder from "./components/AudioRecorder";
import ResultCard from "./components/ResultCard";
import { streamFactCheck, transcribeAudio } from "./services/api";

function App() {
  const [mode, setMode] = useState("verify");
  const [dark, setDark] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark' || 
        (!localStorage.getItem('theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
    return false;
  });

  // Separate state for each mode
  const [modeData, setModeData] = useState({
    verify: {
      query: "",
      response: "",
      meta: null,
      submittedInput: "",
      loading: false,
      mediaStatus: "",
      abortController: null,
      requestSeq: 0,
    },
    summarize: {
      query: "",
      response: "",
      meta: null,
      submittedInput: "",
      loading: false,
      mediaStatus: "",
      abortController: null,
      requestSeq: 0,
    },
  });

  // Get current mode data
  const currentData = modeData[mode];
  
  // Setter function for current mode
  const setCurrentModeData = (updates) => {
    setModeData((prev) => ({
      ...prev,
      [mode]: {
        ...prev[mode],
        ...updates,
      },
    }));
  };

  // Expose current mode data through individual setters for compatibility
  const setQuery = (value) => {
    setCurrentModeData({ query: typeof value === "function" ? value(currentData.query) : value });
  };
  const setResponse = (value) => {
    setCurrentModeData({ response: typeof value === "function" ? value(currentData.response) : value });
  };
  const setMeta = (value) => {
    setCurrentModeData({ meta: typeof value === "function" ? value(currentData.meta) : value });
  };
  const setSubmittedInput = (value) => {
    setCurrentModeData({ submittedInput: typeof value === "function" ? value(currentData.submittedInput) : value });
  };
  const setLoading = (value) => {
    setCurrentModeData({ loading: typeof value === "function" ? value(currentData.loading) : value });
  };
  const setMediaStatus = (value) => {
    setCurrentModeData({ mediaStatus: typeof value === "function" ? value(currentData.mediaStatus) : value });
  };
  const setAbortController = (value) => {
    setCurrentModeData({ abortController: value });
  };
  const setRequestSeq = (value) => {
    setCurrentModeData({ requestSeq: typeof value === "function" ? value(currentData.requestSeq) : value });
  };

  const scrollRef = useRef(null);
  const modeRef = useRef(mode);
  const requestSeqRef = useRef({ verify: 0, summarize: 0 });

  useEffect(() => {
    modeRef.current = mode;
  }, [mode]);

  useEffect(() => {
    if (dark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      document.documentElement.style.colorScheme = "dark";
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      document.documentElement.style.colorScheme = "light";
    }
  }, [dark]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [currentData.response]);

  const handleSubmit = async () => {
    if (!currentData.query.trim()) return;

    if (currentData.abortController) {
      currentData.abortController.abort();
    }
    const controller = new AbortController();
    setAbortController(controller);
    const newSeq = currentData.requestSeq + 1;
    setRequestSeq(newSeq);
    const modeAtSubmit = mode;
    requestSeqRef.current[modeAtSubmit] = newSeq;
    const submitted = currentData.query.trim();

    setSubmittedInput(submitted);
    setResponse("");
    setMeta(null);
    setLoading(true);

    try {
      await streamFactCheck(submitted, modeAtSubmit, (chunk) => {
        const stale =
          requestSeqRef.current[modeAtSubmit] !== newSeq ||
          modeRef.current !== modeAtSubmit;
        if (stale) return;

        if (chunk.type === "text") {
          setModeData((prev) => ({
            ...prev,
            [modeAtSubmit]: {
              ...prev[modeAtSubmit],
              response: prev[modeAtSubmit].response + chunk.data,
            },
          }));
        } else if (chunk.type === "start") {
          // Stream is starting
          setModeData((prev) => ({
            ...prev,
            [modeAtSubmit]: {
              ...prev[modeAtSubmit],
              response: "Generating verdict...",
            },
          }));
        } else if (chunk.type === "status") {
          setModeData((prev) => ({
            ...prev,
            [modeAtSubmit]: {
              ...prev[modeAtSubmit],
              mediaStatus: chunk.data || "",
            },
          }));
        } else if (chunk.type === "meta") {
          setModeData((prev) => ({
            ...prev,
            [modeAtSubmit]: {
              ...prev[modeAtSubmit],
              meta: chunk.data,
              loading: false,
              mediaStatus: "",
            },
          }));
        }
      }, controller.signal);
    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }
      console.error("Fact check failed:", error);
      setLoading(false);
      setResponse("An error occurred during verification. Please try again.");
    } finally {
      setModeData((prev) => {
        if (prev[modeAtSubmit].abortController === controller) {
          return {
            ...prev,
            [modeAtSubmit]: {
              ...prev[modeAtSubmit],
              abortController: null,
            },
          };
        }
        return prev;
      });
    }
  };

  const handleAudioReady = async (blob) => {
    if (mode !== "verify") {
      setMediaStatus("Speech input is available only in Verify Mode.");
      return;
    }
    setMediaStatus("Transcribing audio...");
    try {
      const data = await transcribeAudio(blob);
      const english = data?.transcript_english || data?.transcript || "";
      if (english) {
        setQuery((prev) => (prev ? `${prev} ${english}` : english));
        setMediaStatus("Audio transcribed and added to input.");
      } else {
        setMediaStatus("No speech detected in recording.");
      }
    } catch (error) {
      console.error("Audio transcription failed:", error);
      setMediaStatus("Audio transcription failed.");
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
                onClick={() => setMode("summarize")}
                className={`px-4 py-1.5 rounded-full transition-all duration-300 ${mode === 'summarize' ? 'bg-white dark:bg-slate-700 shadow-md text-brand scale-105' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
              >
                Summarize Mode
              </button>
              <button
                onClick={() => setMode("verify")}
                className={`px-4 py-1.5 rounded-full transition-all duration-300 ${mode === 'verify' ? 'bg-white dark:bg-slate-700 shadow-md text-brand scale-105' : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'}`}
              >
                Verify Mode
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
                query={currentData.query} 
                setQuery={setQuery} 
                onSubmit={handleSubmit}
                placeholder={mode === "summarize" ? "Paste a trusted news URL for summary..." : "Paste a claim/news text to verify..."}
                multiline={mode !== "summarize"}
              />
            </div>
            
            <div className="flex items-center justify-between p-3">
              <div className="flex items-center gap-2">
                {mode === "verify" && (
                  <div className="flex items-center gap-2">
                    <AudioRecorder onAudioReady={handleAudioReady} />
                    <span className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase tracking-wider">Mic</span>
                  </div>
                )}
                <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-1" />
                <span className="text-[10px] text-slate-400 font-bold uppercase tracking-tighter hidden sm:inline">
                  {mode === 'summarize' ? 'Trusted-source summarization active' : 'Evidence verification active'}
                </span>
              </div>
              
              <button
                onClick={handleSubmit}
                disabled={currentData.loading || !currentData.query.trim()}
                className={`
                  flex items-center gap-2 px-8 py-3 rounded-2xl font-bold transition-all duration-300 shadow-xl
                  ${currentData.loading || !currentData.query.trim() 
                    ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 cursor-not-allowed shadow-none' 
                    : 'bg-brand hover:bg-brand-dark text-white hover:scale-105 active:scale-95 shadow-brand/30 hover:shadow-brand/40'}
                `}
              >
                {currentData.loading ? (
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
        {currentData.mediaStatus && (
          <div className="mb-4 text-xs font-semibold text-brand">{currentData.mediaStatus}</div>
        )}
        <AnimatePresence mode="wait">
          {(currentData.response || currentData.loading) && (
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
                  {mode === "summarize" ? "Summary Report" : "Verification Report"}
                </h3>
                {currentData.meta && (
                  <motion.div 
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border ${
                      parseFloat(currentData.meta.confidence) > 0.7 
                      ? 'bg-green-100/50 text-green-700 border-green-200 dark:bg-green-900/30 dark:text-green-400 dark:border-green-800' 
                      : 'bg-amber-100/50 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800'
                    }`}
                  >
                    {Math.round(parseFloat(currentData.meta.confidence) * 100)}% Confidence
                  </motion.div>
                )}
              </div>

              <div 
                ref={scrollRef}
                className="p-8 max-h-[600px] overflow-y-auto leading-relaxed text-slate-700 dark:text-slate-300"
              >
                {currentData.loading && !currentData.response && (
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
                  {currentData.submittedInput && (
                    <div className="mb-4 p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-700/60 text-sm">
                      <span className="font-semibold">Submitted Input:</span> {currentData.submittedInput}
                    </div>
                  )}
                  {currentData.response}
                  {currentData.loading && currentData.response && (
                    <span className="inline-block w-2 h-6 bg-brand ml-2 animate-pulse" />
                  )}
                </div>

                {currentData.meta && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <ResultCard meta={currentData.meta} />
                    {currentData.meta.summarize_error && (
                      <p className="mt-4 text-xs text-amber-600 dark:text-amber-400 font-semibold">
                        {currentData.meta.summarize_error}
                      </p>
                    )}
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
