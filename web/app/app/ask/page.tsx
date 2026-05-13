import { AskWorkspacePage } from "@/components/workbench/ask-workspace";

type AskPageProps = {
  searchParams: Promise<{
    q?: string;
    topicId?: string;
    mode?: string;
    continueFromAskTurnId?: string;
  }>;
};

export default async function AskPage({ searchParams }: AskPageProps) {
  return await AskWorkspacePage({ basePath: "/app/ask", searchParams });
}
