"use client";

import type { ResearchAskMode, ResearchAskResponse } from "@/lib/types";
import { AskAnswerCard } from "@/components/workbench/ask-answer-card";
import { PanelCard } from "@/components/ui/panel-card";
import { SelectionDeposit } from "@/components/workbench/selection-deposit";
import type { ReactNode } from "react";

type AskAnswerPanelProps = {
  answer: ResearchAskResponse | null;
  mode: ResearchAskMode;
  continueFromAskTurnId?: string;
  askHref: (nextQuestion: string, nextMode?: ResearchAskMode) => string;
  writebackAction: ReactNode;
  runId?: string;
};

export function AskAnswerPanel({
  answer,
  mode,
  continueFromAskTurnId,
  askHref,
  writebackAction,
  runId,
}: AskAnswerPanelProps) {
  return (
    <PanelCard className="p-8">
      {answer ? (
        <SelectionDeposit answerId={answer.id} runId={runId}>
          <AskAnswerCard
            answer={answer}
            continueFromAskTurnId={continueFromAskTurnId}
            mode={mode}
            renderFollowUpHref={(nextQuestion: string, nextMode?: ResearchAskMode) =>
              askHref(nextQuestion, nextMode ?? mode)
            }
            writebackAction={writebackAction}
          />
        </SelectionDeposit>
      ) : (
        <AskAnswerCard
          answer={answer}
          continueFromAskTurnId={continueFromAskTurnId}
          mode={mode}
          renderFollowUpHref={(nextQuestion: string, nextMode?: ResearchAskMode) =>
            askHref(nextQuestion, nextMode ?? mode)
          }
          writebackAction={writebackAction}
        />
      )}
    </PanelCard>
  );
}
