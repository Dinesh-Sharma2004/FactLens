import ConfidenceGraph from "./ConfidenceGraph";
import { motion } from "framer-motion";

export default function ResultCard({ meta }) {
  return (
    <div className="mt-8 pt-8 border-t border-slate-100 dark:border-slate-800">
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
                    {new URL(n.url).hostname}
                  </span>
                </motion.a>
              ))
            ) : (
              <p className="text-sm text-slate-500 italic">No external sources cited for this verification.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
