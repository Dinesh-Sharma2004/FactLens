import { useState } from "react";
import { motion } from "framer-motion";
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
  const [dark, setDark] = useState(false);

  const handleSubmit = async () => {
    if (!query.trim()) return;

    setResponse("");
    setMeta(null);
    setLoading(true);

    await streamFactCheck(query, mode, (chunk) => {
      if (chunk.type === "text") {
        setResponse((prev) => prev + chunk.data);
      } else if (chunk.type === "meta") {
        setMeta(chunk.data);
        setLoading(false);
      }
    });
  };

  return (
    <div className={dark ? "dark" : ""}>

      <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-200 dark:from-black dark:to-gray-900">

        {/* HEADER */}
        <div className="flex justify-between items-center px-6 py-4 border-b dark:border-gray-800">
          <h1 className="text-xl font-semibold">ET FactLens</h1>

          <button
            onClick={() => setDark(!dark)}
            className="px-3 py-1 rounded-lg bg-gray-200 dark:bg-gray-800"
          >
            {dark ? "☀️" : "🌙"}
          </button>
        </div>

        <div className="max-w-3xl mx-auto p-6">

          {/* HERO */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center mb-8"
          >
            <h2 className="text-3xl font-bold">
              Verify Information Instantly
            </h2>
          </motion.div>

          {/* INPUT */}
          <div className="glass bg-white/70 dark:bg-white/10 p-6 rounded-2xl shadow-md">

            <InputBox query={query} setQuery={setQuery} onSubmit={handleSubmit} />

            <div className="flex justify-between mt-4 flex-wrap gap-3">

              <div className="flex gap-2">
                <button
                  onClick={handleSubmit}
                  className="bg-red-600 hover:bg-red-800 text-white px-5 py-2 rounded-full shadow"
                >
                  {loading ? "Checking..." : "Verify"}
                </button>

                <button
                  onClick={() => setMode("rag")}
                  className={`px-4 py-2 rounded-full ${
                    mode === "rag" ? "bg-red-600 text-white" : "bg-gray-200"
                  }`}
                >
                  RAG
                </button>

                <button
                  onClick={() => setMode("no_rag")}
                  className={`px-4 py-2 rounded-full ${
                    mode === "no_rag" ? "bg-red-600 text-white" : "bg-gray-200"
                  }`}
                >
                  No-RAG
                </button>
              </div>

              <div className="flex gap-2">
                <AudioRecorder setQuery={setQuery} />
                <ImageUpload />
              </div>

            </div>

          </div>

          {/* RESULT */}
          <motion.div className="mt-6 glass bg-white/70 dark:bg-white/10 p-6 rounded-2xl shadow-md">

            <h3 className="font-semibold">Result</h3>

            {loading && <p className="text-gray-400 italic mt-2">Thinking...</p>}

            {!response && !loading && (
              <p className="text-gray-400 mt-3">Enter a claim to verify...</p>
            )}

            <p className="mt-3 whitespace-pre-wrap">
              {response}
              <span className="animate-pulse">|</span>
            </p>

            {meta && <ResultCard meta={meta} />}

          </motion.div>

        </div>
      </div>
    </div>
  );
}

export default App;
