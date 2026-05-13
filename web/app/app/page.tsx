import { AskWorkspacePage } from "@/components/workbench/ask-workspace";

type WorkbenchPageProps = {
  searchParams: Promise<{
    q?: string;
    topicId?: string;
    mode?: string;
    continueFromAskTurnId?: string;
  }>;
};

export default async function WorkbenchPage({ searchParams }: WorkbenchPageProps) {
  return await AskWorkspacePage({ searchParams });
}
