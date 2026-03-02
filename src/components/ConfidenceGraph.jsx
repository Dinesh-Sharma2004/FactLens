export default function ConfidenceGraph({ data }) {
  if (!data) return null;

  return (
    <div className="mt-3 space-y-2">
      {Object.entries(data).map(([k, v]) => (
        <div key={k}>
          <p className="text-sm">{k}</p>
          <div className="bg-gray-200 h-2 rounded">
            <div className="bg-red-600 h-2 rounded" style={{ width: `${v * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
