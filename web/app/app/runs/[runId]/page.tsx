import { RunInspector } from "@/components/workbench/run-inspector";

export default async function RunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  return <RunInspector runId={runId} />;
}
