export default function InputBox({ query, setQuery, onSubmit }) {
  return (
    <input
      type="text"
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyDown={(e) => e.key === "Enter" && onSubmit()}
      placeholder="Ask anything..."
      className="w-full p-4 border rounded-xl focus:ring-2 focus:ring-red-600"
    />
  );
}
