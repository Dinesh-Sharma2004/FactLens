import ConfidenceGraph from "./ConfidenceGraph";
import { motion } from "framer-motion";

function getHost(url) {
  try {
    return new URL(url).hostname;
  } catch {
    return "source";
  }
}

export default function ResultCard({ meta }) {
  if (meta.mode === "summarize") {
    return (
      <div className="mt-8 pt-8 border-t border-slate-100 dark:border-slate-800">
        {meta.summary_struct && (
          <div className="mb-6 p-4 rounded-xl bg-emerald-50/70 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30">
            <p className="text-xs font-bold uppercase tracking-widest text-emerald-700 dark:text-emerald-300 mb-2">
              Structured Summary
            </p>
            <p className="text-xs"><span className="font-semibold">Summary:</span> {meta.summary_struct.summary || "N/A"}</p>
            <p className="text-xs mt-1"><span className="font-semibold">Key Event:</span> {meta.summary_struct.key_event || "N/A"}</p>
            <p className="text-xs mt-1"><span className="font-semibold">Timeline:</span> {meta.summary_struct.timeline || "N/A"}</p>
          </div>
        )}

        <section>
          <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
            Source URL
          </h4>
          <div className="space-y-3">
            {meta.news && meta.news.length > 0 ? (
              meta.news.map((n, i) => (
                <motion.a
                  key={i}
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex flex-col p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 hover:bg-brand/5 dark:hover:bg-brand/10 border border-transparent hover:border-brand/20 transition-all group"
                >
                  <span className="font-semibold text-sm line-clamp-1 group-hover:text-brand transition-colors">
                    {n.title}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-1">{getHost(n.url)}</span>
                </motion.a>
              ))
            ) : (
              <p className="text-sm text-slate-500 italic">No source URL available.</p>
            )}
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="mt-8 pt-8 border-t border-slate-100 dark:border-slate-800">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
          <p className="text-[10px] uppercase text-slate-400 font-bold tracking-widest">Verdict</p>
          <p className="font-semibold mt-1">{meta.verdict || "Unknown"}</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
          <p className="text-[10px] uppercase text-slate-400 font-bold tracking-widest">Latency</p>
          <p className="font-semibold mt-1">{meta.latency}s</p>
        </div>
        <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60">
          <p className="text-[10px] uppercase text-slate-400 font-bold tracking-widest">Support Ratio</p>
          <p className="font-semibold mt-1">{Math.round((meta.metrics?.support_ratio || 0) * 100)}%</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <section>
          <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
            Confidence Breakdown
          </h4>
          <ConfidenceGraph data={meta.confidence_breakdown} />
        </section>

        <section>
          <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
            Source Citations
          </h4>
          <div className="space-y-3">
            {meta.news && meta.news.length > 0 ? (
              meta.news.map((n, i) => (
                <motion.a
                  key={i}
                  href={n.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.1 }}
                  className="flex flex-col p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 hover:bg-brand/5 dark:hover:bg-brand/10 border border-transparent hover:border-brand/20 transition-all group"
                >
                  <span className="font-semibold text-sm line-clamp-1 group-hover:text-brand transition-colors">
                    {n.title}
                  </span>
                  <span className="text-[10px] text-slate-400 mt-1 flex items-center gap-1">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                    {getHost(n.url)}
                  </span>
                </motion.a>
              ))
            ) : (
              <p className="text-sm text-slate-500 italic">No external sources cited for this verification.</p>
            )}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-8">
        <section>
          <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
            Correct News Context
          </h4>
          <div className="space-y-3">
            {meta.corrected_news?.length ? (
              meta.corrected_news.map((item, idx) => (
                <a
                  key={`${item.url}-${idx}`}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block p-3 rounded-xl bg-emerald-50/70 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30"
                >
                  <p className="text-sm font-semibold">{item.headline}</p>
                  <p className="text-xs text-slate-500 mt-1">{item.summary}</p>
                </a>
              ))
            ) : (
              <p className="text-sm text-slate-500 italic">No corrected news available.</p>
            )}
          </div>
        </section>

        <section>
          <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
            Fake News Error Analysis
          </h4>
          <div className="space-y-3">
            {meta.fake_news_errors?.length ? (
              meta.fake_news_errors.map((item, idx) => (
                <div
                  key={`${item.error_type}-${idx}`}
                  className="p-3 rounded-xl bg-amber-50/70 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800/30"
                >
                  <p className="text-sm font-semibold text-amber-700 dark:text-amber-300">{item.error_type}</p>
                  <p className="text-xs mt-1 text-slate-600 dark:text-slate-300">{item.details}</p>
                  <p className="text-xs mt-1"><span className="font-semibold">Fix:</span> {item.correction}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500 italic">No fake-news pattern detected.</p>
            )}
          </div>
        </section>
      </div>

      {/* Cache & Evidence Source Info */}
      {meta.evidence_source && (
        <div className="mt-8 p-4 rounded-xl bg-blue-50/70 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800/30">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-700 dark:text-blue-300 mb-2">
            Evidence Source & Cache Info
          </p>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-slate-600 dark:text-slate-400">Source:</p>
              <p className="font-semibold text-blue-700 dark:text-blue-300 capitalize">{meta.evidence_source}</p>
            </div>
            {meta.cache_stats && (
              <>
                <div>
                  <p className="text-slate-600 dark:text-slate-400">Cache Usage:</p>
                  <p className="font-semibold">{meta.cache_stats.usage_percent}%</p>
                </div>
                <div>
                  <p className="text-slate-600 dark:text-slate-400">Cached Items:</p>
                  <p className="font-semibold">{meta.cache_stats.total_entries}</p>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* References Section */}
      {meta.references && meta.references.length > 0 && (
        <section className="mt-8">
          <h4 className="text-sm font-bold uppercase tracking-widest text-slate-400 mb-4">
            References
          </h4>
          <div className="space-y-2 text-xs">
            {meta.references.map((ref, idx) => (
              <div
                key={ref.ref_id || idx}
                className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200/60 dark:border-slate-700/60"
              >
                <p className="font-semibold text-slate-700 dark:text-slate-300">
                  {ref.ref_id}. {ref.source}
                </p>
                <p className="text-slate-600 dark:text-slate-400 mt-1 line-clamp-2">{ref.title}</p>
                <a
                  href={ref.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-brand hover:underline mt-1 inline-flex items-center gap-1"
                >
                  View Source
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
