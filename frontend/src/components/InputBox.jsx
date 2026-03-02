export default function InputBox({ query, setQuery, onSubmit, placeholder }) {
  return (
    <textarea
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          onSubmit();
        }
      }}
      placeholder={placeholder || "Ask anything..."}
      className="w-full min-h-[120px] p-6 bg-transparent border-none focus:ring-0 text-lg resize-none placeholder:text-slate-400 dark:placeholder:text-slate-600"
    />
  );
}
