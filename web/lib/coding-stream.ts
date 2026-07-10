"use client";

import { resolveApiBaseUrl } from "@/lib/server-api";
import { postInkdeskJson } from "@/lib/server-api";

// ── SSE 事件类型 ──

export type CodingSseEvent =
  | { type: "connected"; data: { run_id: string } }
  | { type: "session_started"; data: { cwd: string } }
  | { type: "assistant_message"; data: { text: string; tool_calls: ToolCall[] } }
  | { type: "tool_result"; data: { results: ToolResult[] } }
  | { type: "partial_message"; data: { event: Record<string, unknown> } }
  | { type: "permission_request"; data: PermissionRequestData }
  | { type: "tool_call_detected"; data: { tool_name: string; tool_input: Record<string, unknown> } }
  | { type: "result_message"; data: ResultMessageData }
  | { type: "completed"; data: CompletedData }
  | { type: "error"; data: { message: string } }
  | { type: "aborted"; data: { reason: string } }
  | { type: "stream_end"; data: { finished: boolean } };

export type ToolCall = {
  id: string;
  name: string;
  input: Record<string, unknown>;
};

export type ToolResult = {
  tool_use_id: string;
  content: string;
  is_error: boolean;
};

export type PermissionRequestData = {
  request_id: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
  created_at: number;
};

export type ResultMessageData = {
  subtype: string;
  is_error: boolean;
  num_turns: number;
  total_cost_usd: number;
  duration_ms: number;
  session_id: string;
};

export type CompletedData = {
  result: string;
  success: boolean;
  error: string | null;
  cost_usd: number | null;
  duration_ms: number | null;
  session_id: string | null;
  num_turns: number | null;
  tool_uses: string[];
  tool_records: ToolResult[];
  aborted: boolean;
};

// ── 对话消息模型（供 UI 渲染） ──

export type ConversationMessage =
  | { kind: "assistant_text"; text: string }
  | { kind: "tool_call"; call: ToolCall }
  | { kind: "tool_result"; result: ToolResult }
  | { kind: "status"; text: string };

// ── SSE 客户端 ──

export type CodingStreamCallbacks = {
  onEvent: (event: CodingSseEvent) => void;
  onError?: (error: Event) => void;
  onOpen?: () => void;
};

export class CodingStreamClient {
  private eventSource: EventSource | null = null;
  private callbacks: CodingStreamCallbacks;

  constructor(
    private runId: string,
    callbacks: CodingStreamCallbacks,
  ) {
    this.callbacks = callbacks;
  }

  connect(): void {
    const baseUrl = resolveApiBaseUrl();
    if (!baseUrl) {
      this.callbacks.onEvent({
        type: "error",
        data: { message: "Inkdesk API base URL is not configured" },
      });
      return;
    }

    const url = `${baseUrl}/runs/${this.runId}/coding/stream`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      this.callbacks.onOpen?.();
    };

    // 监听所有命名事件
    const eventTypes = [
      "connected",
      "session_started",
      "assistant_message",
      "tool_result",
      "partial_message",
      "permission_request",
      "tool_call_detected",
      "result_message",
      "completed",
      "error",
      "aborted",
      "stream_end",
    ];

    for (const type of eventTypes) {
      this.eventSource.addEventListener(type, (raw: MessageEvent) => {
        try {
          const data = raw.data ? JSON.parse(raw.data) : {};
          this.callbacks.onEvent({ type: type as CodingSseEvent["type"], data });
        } catch {
          // 忽略解析错误
        }
      });
    }

    this.eventSource.onerror = (error) => {
      this.callbacks.onError?.(error);
    };
  }

  close(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

// ── API 调用 ──

export async function respondCodingPermission(
  runId: string,
  requestId: string,
  allow: boolean,
  reason?: string,
): Promise<{ ok: boolean }> {
  return postInkdeskJson<{ ok: boolean }>(
    `/runs/${runId}/coding/permission/respond`,
    { request_id: requestId, allow, reason: reason ?? null },
  );
}

export async function abortCoding(runId: string): Promise<{ ok: boolean }> {
  return postInkdeskJson<{ ok: boolean }>(`/runs/${runId}/coding/abort`, {});
}
