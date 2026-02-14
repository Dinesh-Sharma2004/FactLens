import ConfidenceGraph from "./ConfidenceGraph";

export default function ResultCard({ meta }) {
  return (
    <div className="mt-4">
      <p><b>Confidence:</b> {meta.confidence}</p>
      <ConfidenceGraph data={meta.confidence_breakdown} />

      <h4 className="mt-4">News</h4>
      {meta.news.map((n, i) => (
        <a key={i} href={n.url} target="_blank" className="block text-blue-500">
          {n.title}
        </a>
      ))}
    </div>
  );
}
