import { motion } from "framer-motion";

export default function ConfidenceGraph({ data }) {
  if (!data) return null;

  return (
    <div className="space-y-4">
      {Object.entries(data).map(([k, v], i) => (
        <div key={k} className="space-y-1.5">
          <div className="flex justify-between items-center text-xs font-medium">
            <span className="capitalize text-slate-500 dark:text-slate-400">{k.replace('_', ' ')}</span>
            <span className="text-brand font-bold">{Math.round(v * 100)}%</span>
          </div>
          <div className="h-2 w-full bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${v * 100}%` }}
              transition={{ duration: 1, delay: i * 0.1, ease: "easeOut" }}
              className="h-full bg-gradient-to-r from-brand to-brand-dark rounded-full"
            />
          </div>
        </div>
      ))}
    </div>
  );
}
