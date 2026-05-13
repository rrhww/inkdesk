export function buildIngestRevalidationPaths(topicId?: string | null) {
  const paths = ["/app", "/app/ask", "/app/ingest", "/app/wiki", "/app/raw"];
  if (topicId?.trim()) {
    paths.push(`/app/wiki/${topicId.trim()}`);
  }
  return paths;
}
