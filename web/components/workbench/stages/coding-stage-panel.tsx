"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  executeCoding,
  extractCodingBriefing,
  extractCodingResult,
  submitStageOutput,
  getDevRun,
} from "@/lib/research";
import {
  CodingStreamClient,
  respondCodingPermission,
  abortCoding,
  type CodingSseEvent,
  type ConversationMessage,
  type PermissionRequestData,
  type CompletedData,
} from "@/lib/coding-stream";
import type { DevRun, DevRunStageStatus } from "@/lib/types";
import { PanelCard } from "@/components/ui/panel-card";
import { PermissionDialog } from "./permission-dialog";

type CodingStagePanelProps = {
  run: DevRun;
  stageStatus: DevRunStageStatus;
  onRunUpdate: (run: DevRun) => void;
};

export function CodingStagePanel({ run, stageStatus, onRunUpdate }: CodingStagePanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [pendingPermission, setPendingPermission] = useState<PermissionRequestData | null>(null);
  const [completedData, setCompletedData] = useState<CompletedData | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [aborting, setAborting] = useState(false);

  const streamClientRef = useRef<CodingStreamClient | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const runIdRef = useRef(run.id);

  const briefing = extractCodingBriefing(run);
  const result = extractCodingResult(run);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 清理 SSE 连接
  useEffect(() => {
    return () => {
      streamClientRef.current?.close();
      streamClientRef.current = null;
    };
  }, []);

  const appendMessage = useCallback((msg: ConversationMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const handleSseEvent = useCallback(
    (event: CodingSseEvent) => {
      switch (event.type) {
        case "connected":
          appendMessage({ kind: "status", text: "SSE 连接已建立" });
          break;
        case "session_started":
          appendMessage({ kind: "status", text: `Claude Code 会话已启动 (cwd: ${event.data.cwd})` });
          break;
        case "assistant_message":
          if (event.data.text) {
            appendMessage({ kind: "assistant_text", text: event.data.text });
          }
          for (const call of event.data.tool_calls) {
            appendMessage({ kind: "tool_call", call });
          }
          break;
        case "tool_result":
          for (const r of event.data.results) {
            appendMessage({ kind: "tool_result", result: r });
          }
          break;
        case "permission_request":
          setPendingPermission(event.data);
          break;
        case "completed":
          setCompletedData(event.data);
          setStreaming(false);
          setPendingPermission(null);
          if (event.data.aborted) {
            appendMessage({ kind: "status", text: "会话已中断" });
          } else if (event.data.success) {
            appendMessage({ kind: "status", text: `执行完成 (${event.data.num_turns} 轮, $${event.data.cost_usd?.toFixed(2) ?? "N/A"})` });
          } else {
            appendMessage({ kind: "status", text: `执行失败: ${event.data.error ?? "未知错误"}` });
          }
          // 刷新 run 数据
          getDevRun(runIdRef.current).then(onRunUpdate).catch(() => {});
          break;
        case "error":
          setStreamError(event.data.message);
          setStreaming(false);
          break;
        case "aborted":
          appendMessage({ kind: "status", text: `会话中断: ${event.data.reason}` });
          break;
        case "stream_end":
          streamClientRef.current?.close();
          streamClientRef.current = null;
          break;
        // partial_message 和 tool_call_detected 不单独渲染（太频繁）
        case "partial_message":
        case "tool_call_detected":
        case "result_message":
          break;
      }
    },
    [appendMessage, onRunUpdate],
  );

  const startStream = useCallback(() => {
    // 关闭旧连接
    streamClientRef.current?.close();
    setMessages([]);
    setCompletedData(null);
    setStreamError(null);
    setPendingPermission(null);
    setStreaming(true);

    const client = new CodingStreamClient(runIdRef.current, {
      onEvent: handleSseEvent,
      onError: () => {
        // EventSource 在连接关闭时会触发 onerror，如果还在 streaming 状态说明是异常断开
        setStreaming(false);
      },
    });
    streamClientRef.current = client;
    client.connect();
  }, [handleSseEvent]);

  const handleSkip = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await submitStageOutput(run.id, "coding", {
        summary: "手动跳过 coding 阶段，不调用 Claude Code CLI",
        skipped: true,
        skipReason: "用户选择手动批准",
      });
      onRunUpdate(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "跳过编码阶段失败");
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    setLoading(true);
    setError(null);
    try {
      const updated = await executeCoding(run.id);
      onRunUpdate(updated);
      // execute 返回后，后端已启动后台 task，连 SSE 接收流
      startStream();
    } catch (e) {
      setError(e instanceof Error ? e.message : "启动 Claude Code 失败");
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionRespond = async (allow: boolean, reason?: string) => {
    if (!pendingPermission) return;
    try {
      await respondCodingPermission(run.id, pendingPermission.request_id, allow, reason);
      setPendingPermission(null);
      appendMessage({
        kind: "status",
        text: `权限请求已${allow ? "放行" : "拒绝"}: ${pendingPermission.tool_name}`,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "权限回应失败");
    }
  };

  const handleAbort = async () => {
    setAborting(true);
    try {
      await abortCoding(run.id);
      appendMessage({ kind: "status", text: "正在中断会话…" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "中断失败");
    } finally {
      setAborting(false);
    }
  };

  // ── pending 状态：显示执行按钮 ──
  if (stageStatus === "pending" || !briefing) {
    return (
      <PanelCard className="p-6">
        <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">编码阶段</div>
        <p className="text-sm text-ink-muted mb-4">
          点击下方按钮，Inkdesk 将组装 Briefing 并启动 Claude Code（交互模式：支持实时对话、权限弹窗、中断）。
        </p>
        {error && (
          <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">{error}</div>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleExecute}
            disabled={loading}
            className="rounded-full bg-ink-primary px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "启动中…" : "启动 Claude Code"}
          </button>
          <button
            onClick={handleSkip}
            disabled={loading}
            className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed"
          >
            跳过，手动批准
          </button>
        </div>
      </PanelCard>
    );
  }

  // ── 流式执行中 ──
  if (streaming || (messages.length > 0 && !completedData && !result)) {
    return (
      <>
        <PanelCard className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted">编码阶段 · 实时对话</div>
            <button
              onClick={handleAbort}
              disabled={aborting}
              className="flex items-center gap-1.5 rounded-full bg-red-50 px-4 py-2 text-xs font-medium text-red-600 hover:bg-red-100 disabled:opacity-40"
            >
              <span className="material-symbols-outlined text-[16px]">stop_circle</span>
              {aborting ? "中断中…" : "中断"}
            </button>
          </div>

          {streamError && (
            <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">
              {streamError}
            </div>
          )}

          {/* 对话流 */}
          <div className="max-h-[480px] overflow-auto space-y-3 mb-4">
            <ConversationView messages={messages} />
            {streaming && messages.length === 0 && (
              <div className="flex items-center gap-3 py-4">
                <div className="w-5 h-5 border-2 border-ink-primary border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-ink-muted">等待 Claude Code 响应…</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <details className="mt-4">
            <summary className="text-xs text-ink-muted cursor-pointer">查看 Briefing</summary>
            <pre className="mt-2 whitespace-pre-wrap text-xs text-ink-text bg-ink-low rounded-2xl p-4 max-h-64 overflow-auto">
{briefing}
            </pre>
          </details>
        </PanelCard>

        {pendingPermission && (
          <PermissionDialog
            request={pendingPermission}
            onRespond={handlePermissionRespond}
          />
        )}
      </>
    );
  }

  // ── 有结果 ──
  const finalResult = completedData ?? (result ? {
    result: result.result,
    success: result.success,
    error: result.error,
    cost_usd: null,
    duration_ms: null,
    session_id: null,
    num_turns: null,
    tool_uses: [],
    tool_records: [],
    aborted: false,
  } : null);

  return (
    <PanelCard className="p-6">
      <div className="text-[11px] uppercase tracking-[0.2em] text-ink-muted mb-4">
        编码结果
        {stageStatus === "completed" && <span className="ml-2 text-green-600">已完成</span>}
      </div>

      {finalResult && (
        <>
          <div className="flex items-center gap-2 mb-4">
            <span className={`material-symbols-outlined text-[20px] ${finalResult.success ? "text-green-600" : "text-red-500"}`}>
              {finalResult.success ? "check_circle" : "error"}
            </span>
            <span className="text-sm font-medium text-ink-text">
              {finalResult.aborted ? "已中断" : finalResult.success ? "执行成功" : "执行失败"}
            </span>
            {finalResult.num_turns != null && (
              <span className="text-xs text-ink-muted ml-2">
                {finalResult.num_turns} 轮 · ${finalResult.cost_usd?.toFixed(2) ?? "N/A"}
              </span>
            )}
          </div>

          {finalResult.error && (
            <div className="mb-4 rounded-2xl bg-ink-errorSoft px-4 py-3 text-sm text-ink-errorText">
              {finalResult.error}
            </div>
          )}

          {/* 对话历史（如果有） */}
          {messages.length > 0 && (
            <div className="mb-4 max-h-96 overflow-auto space-y-3 rounded-2xl bg-ink-low p-4">
              <ConversationView messages={messages} />
            </div>
          )}

          {finalResult.result && (
            <div className="mb-4">
              <div className="text-xs text-ink-muted mb-2">执行输出</div>
              <pre className="whitespace-pre-wrap text-sm text-ink-text bg-ink-low rounded-2xl p-4 max-h-96 overflow-auto">
{finalResult.result}
              </pre>
            </div>
          )}

          {!finalResult.success && !finalResult.aborted && (
            <button
              onClick={handleExecute}
              disabled={loading}
              className="rounded-full bg-ink-low px-5 py-2.5 text-sm font-medium text-ink-text hover:bg-white disabled:opacity-40"
            >
              {loading ? "启动中…" : "重试"}
            </button>
          )}
        </>
      )}

      <details className="mt-4">
        <summary className="text-xs text-ink-muted cursor-pointer">查看 Briefing</summary>
        <pre className="mt-2 whitespace-pre-wrap text-xs text-ink-text bg-ink-low rounded-2xl p-4 max-h-64 overflow-auto">
{briefing}
        </pre>
      </details>
    </PanelCard>
  );
}

// ── 对话渲染子组件 ──

function ConversationView({ messages }: { messages: ConversationMessage[] }) {
  return (
    <>
      {messages.map((msg, idx) => {
        switch (msg.kind) {
          case "assistant_text":
            return (
              <div key={idx} className="rounded-2xl bg-white px-4 py-3 text-sm text-ink-text">
                <div className="text-[10px] uppercase tracking-[0.15em] text-ink-muted mb-1">Claude</div>
                <div className="whitespace-pre-wrap">{msg.text}</div>
              </div>
            );
          case "tool_call":
            return (
              <div key={idx} className="rounded-2xl bg-amber-50 px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="material-symbols-outlined text-[16px] text-amber-600">build</span>
                  <span className="text-[10px] uppercase tracking-[0.15em] text-amber-700">工具调用</span>
                  <code className="text-xs font-mono text-amber-900">{msg.call.name}</code>
                </div>
                <pre className="text-xs font-mono text-amber-900/80 overflow-auto max-h-32">
{JSON.stringify(msg.call.input, null, 2)}
                </pre>
              </div>
            );
          case "tool_result":
            return (
              <div key={idx} className={`rounded-2xl px-4 py-3 ${msg.result.is_error ? "bg-red-50" : "bg-green-50"}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`material-symbols-outlined text-[16px] ${msg.result.is_error ? "text-red-600" : "text-green-600"}`}>
                    {msg.result.is_error ? "error" : "check"}
                  </span>
                  <span className={`text-[10px] uppercase tracking-[0.15em] ${msg.result.is_error ? "text-red-700" : "text-green-700"}`}>
                    {msg.result.is_error ? "执行失败" : "执行结果"}
                  </span>
                </div>
                <pre className={`text-xs font-mono overflow-auto max-h-32 ${msg.result.is_error ? "text-red-900/80" : "text-green-900/80"}`}>
{msg.result.content}
                </pre>
              </div>
            );
          case "status":
            return (
              <div key={idx} className="flex items-center gap-2 py-1 text-xs text-ink-muted">
                <span className="material-symbols-outlined text-[14px]">info</span>
                {msg.text}
              </div>
            );
        }
      })}
    </>
  );
}
