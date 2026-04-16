"use client";

import { useActionState, useEffect, useState } from "react";

import { PanelCard } from "@/components/ui/panel-card";
import { SectionHeading } from "@/components/ui/section-heading";
import { settingsPayloadFromFormData } from "@/lib/settings";
import type { FormState, SettingsRecord } from "@/lib/types";

type SettingsWorkspaceProps = {
  initialSettings: SettingsRecord;
  saveAction?: (
    state: SettingsWorkspaceActionState,
    formData: FormData
  ) => Promise<SettingsWorkspaceActionState> | SettingsWorkspaceActionState;
};

export type SettingsWorkspaceActionState = {
  settings: SettingsRecord;
  saveState: FormState;
  message?: string;
};

async function defaultSaveAction(
  state: SettingsWorkspaceActionState,
  formData: FormData
): Promise<SettingsWorkspaceActionState> {
  return {
    settings: {
      ...settingsPayloadFromFormData(formData),
      security: state.settings.security
    },
    saveState: "success",
    message: "本轮设置已写入本地 mock 配置，可继续用于页面预览。"
  };
}

export function SettingsWorkspace({ initialSettings, saveAction = defaultSaveAction }: SettingsWorkspaceProps) {
  const initialState: SettingsWorkspaceActionState = {
    settings: initialSettings,
    saveState: "idle"
  };
  const [serverState, formAction, isPending] = useActionState(saveAction, initialState);
  const [settings, setSettings] = useState(initialSettings);
  const [saveState, setSaveState] = useState<FormState>("idle");

  useEffect(() => {
    setSettings(serverState.settings);
    setSaveState(serverState.saveState);
  }, [serverState]);

  function resetSettings() {
    setSettings(serverState.settings);
    setSaveState("idle");
  }

  const saveLabel =
    isPending
      ? "保存中..."
      : saveState === "success"
        ? "已保存到主系统"
        : "保存设置";

  function updateSettings(mutator: (current: SettingsRecord) => SettingsRecord) {
    setSettings((current) => mutator(current));
    setSaveState("idle");
  }

  return (
    <form action={formAction}>
      <main className="mx-auto max-w-shell px-6 py-10 lg:px-8">
        <section className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <SectionHeading
            eyebrow="设置"
            title="让主系统更像你的长期工作台"
            description="这里的作者资料、工作台偏好、编辑器默认项和发布默认项都会真实写入后端，并在刷新后继续回显。"
          />
          <div className="flex gap-3">
            <button
              className="rounded-sm bg-white px-4 py-3 text-sm font-semibold text-ink-text shadow-paper"
              onClick={resetSettings}
              type="button"
            >
              恢复已保存值
            </button>
            <button className="rounded-sm bg-ink-primary px-4 py-3 text-sm font-semibold text-white" type="submit">
              {saveLabel}
            </button>
          </div>
        </section>

        {saveState === "success" ? (
          <div className="mb-6 rounded-[20px] bg-ink-primarySoft px-5 py-4 text-sm text-ink-primary">
            {serverState.message ?? "设置已写入主系统，刷新后会继续回显。"}
          </div>
        ) : null}

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_320px]">
          <div className="space-y-6">
            <PanelCard className="p-8">
              <SectionHeading eyebrow="作者公开资料" title="公开输出中显示的信息" description="这些字段将被公开输出首页、文章页和作者侧栏共同消费。" />
              <div className="mt-6 grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-ink-muted">
                  <span>显示名称</span>
                  <input
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text"
                    name="profile.displayName"
                    onChange={(event) =>
                      updateSettings((current) => ({
                        ...current,
                        profile: {
                          ...current.profile,
                          displayName: event.target.value
                        }
                      }))
                    }
                    value={settings.profile.displayName}
                  />
                </label>
                <label className="space-y-2 text-sm text-ink-muted">
                  <span>公开标题</span>
                  <input
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text"
                    name="profile.publicTitle"
                    onChange={(event) =>
                      updateSettings((current) => ({
                        ...current,
                        profile: {
                          ...current.profile,
                          publicTitle: event.target.value
                        }
                      }))
                    }
                    value={settings.profile.publicTitle}
                  />
                </label>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <label className="space-y-2 text-sm text-ink-muted">
                  <span>公开地点</span>
                  <input
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text"
                    name="profile.publicLocation"
                    onChange={(event) =>
                      updateSettings((current) => ({
                        ...current,
                        profile: {
                          ...current.profile,
                          publicLocation: event.target.value
                        }
                      }))
                    }
                    value={settings.profile.publicLocation}
                  />
                </label>
              </div>
              <label className="mt-4 block space-y-2 text-sm text-ink-muted">
                <span>公开摘要</span>
                <textarea
                  className="min-h-28 w-full rounded-[20px] bg-ink-low px-4 py-4 text-ink-text"
                  name="profile.summary"
                  onChange={(event) =>
                    updateSettings((current) => ({
                      ...current,
                      profile: {
                        ...current.profile,
                        summary: event.target.value
                      }
                    }))
                  }
                  value={settings.profile.summary}
                />
              </label>
            </PanelCard>

            <PanelCard className="p-8">
              <SectionHeading eyebrow="主系统显示偏好" title="进入主系统时的默认工作模式" description="这部分决定页头上下文、默认落点和整体工作台节奏。" />
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <label className="space-y-2 text-sm text-ink-muted">
                  <span>默认页</span>
                  <select
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text"
                    name="workbench.defaultPage"
                    onChange={(event) =>
                      updateSettings((current) => ({
                        ...current,
                        workbench: {
                          ...current.workbench,
                          defaultPage: event.target.value
                        }
                      }))
                    }
                    value={settings.workbench.defaultPage}
                  >
                    <option value="/app">Agent 控制台</option>
                    <option value="/app/library">笔记与知识库</option>
                    <option value="/app/plans">任务与计划</option>
                  </select>
                </label>
                <ToggleRow
                  checked={settings.workbench.compactMode}
                  label="紧凑模式"
                  name="workbench.compactMode"
                  onChange={(checked) =>
                    updateSettings((current) => ({
                      ...current,
                      workbench: {
                        ...current.workbench,
                        compactMode: checked
                      }
                    }))
                  }
                />
                <ToggleRow
                  checked={settings.workbench.showContextRibbon}
                  label="上下文信息带"
                  name="workbench.showContextRibbon"
                  onChange={(checked) =>
                    updateSettings((current) => ({
                      ...current,
                      workbench: {
                        ...current.workbench,
                        showContextRibbon: checked
                      }
                    }))
                  }
                />
              </div>
            </PanelCard>

            <PanelCard className="p-8">
              <SectionHeading eyebrow="编辑器默认项" title="知识资产工作台的默认行为" description="这部分决定进入编辑器后的默认视图与保存节奏。" />
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <label className="space-y-2 text-sm text-ink-muted">
                  <span>默认视图</span>
                  <select
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text"
                    name="editor.defaultView"
                    onChange={(event) =>
                      updateSettings((current) => ({
                        ...current,
                        editor: {
                          ...current.editor,
                          defaultView: event.target.value as SettingsRecord["editor"]["defaultView"]
                        }
                      }))
                    }
                    value={settings.editor.defaultView}
                  >
                    <option value="edit">编辑</option>
                    <option value="preview">预览</option>
                    <option value="read">只读</option>
                  </select>
                </label>
                <ToggleRow
                  checked={settings.editor.autoSave}
                  label="自动保存"
                  name="editor.autoSave"
                  onChange={(checked) =>
                    updateSettings((current) => ({
                      ...current,
                      editor: {
                        ...current.editor,
                        autoSave: checked
                      }
                    }))
                  }
                />
                <ToggleRow
                  checked={settings.editor.publishReminder}
                  label="发布提醒"
                  name="editor.publishReminder"
                  onChange={(checked) =>
                    updateSettings((current) => ({
                      ...current,
                      editor: {
                        ...current.editor,
                        publishReminder: checked
                      }
                    }))
                  }
                />
              </div>
            </PanelCard>

            <PanelCard className="p-8">
              <SectionHeading eyebrow="发布默认项" title="发布到公开输出时的默认规则" description="发布仍然是次级模块，但在这里把它的默认行为固定下来。" />
              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <label className="space-y-2 text-sm text-ink-muted">
                  <span>默认可见范围</span>
                  <select
                    className="w-full rounded-sm bg-ink-low px-4 py-3 text-ink-text"
                    name="publish.defaultAudience"
                    onChange={(event) =>
                      updateSettings((current) => ({
                        ...current,
                        publish: {
                          ...current.publish,
                          defaultAudience: event.target.value as SettingsRecord["publish"]["defaultAudience"]
                        }
                      }))
                    }
                    value={settings.publish.defaultAudience}
                  >
                    <option value="public">公开输出</option>
                    <option value="private">仅主系统</option>
                  </select>
                </label>
                <ToggleRow
                  checked={settings.publish.showProvenance}
                  label="显示来源信息"
                  name="publish.showProvenance"
                  onChange={(checked) =>
                    updateSettings((current) => ({
                      ...current,
                      publish: {
                        ...current.publish,
                        showProvenance: checked
                      }
                    }))
                  }
                />
                <ToggleRow
                  checked={settings.publish.highlightRecentUpdates}
                  label="高亮最近更新"
                  name="publish.highlightRecentUpdates"
                  onChange={(checked) =>
                    updateSettings((current) => ({
                      ...current,
                      publish: {
                        ...current.publish,
                        highlightRecentUpdates: checked
                      }
                    }))
                  }
                />
              </div>
            </PanelCard>
          </div>

          <aside className="space-y-6">
            <PanelCard className="p-6">
              <SectionHeading eyebrow="会话与安全" title="主人入口与会话信息" description="安全字段由后端派生，只读展示，不允许在浏览器端覆盖。" />
              <dl className="mt-5 space-y-3 text-sm text-ink-muted">
                <div className="flex justify-between gap-4">
                  <dt>主人邮箱</dt>
                  <dd className="text-ink-text">{settings.security.ownerEmail}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt>入口模式</dt>
                  <dd className="text-ink-text">{settings.security.sessionMode}</dd>
                </div>
                <div className="flex justify-between gap-4">
                  <dt>会话时长</dt>
                  <dd className="text-ink-text">{settings.security.sessionDurationLabel}</dd>
                </div>
              </dl>
            </PanelCard>

            <PanelCard className="p-6">
              <SectionHeading eyebrow="当前说明" title="设置页的实现边界" description="本页已经接到真实后端设置接口；刷新页面时会重新读取已持久化值。" />
            </PanelCard>
          </aside>
        </div>
      </main>
    </form>
  );
}

type ToggleRowProps = {
  label: string;
  name: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
};

function ToggleRow({ label, name, checked, onChange }: ToggleRowProps) {
  return (
    <label className="flex items-center justify-between gap-4 rounded-[20px] bg-ink-low px-4 py-4 text-sm text-ink-muted">
      <span>{label}</span>
      <input name={name} type="hidden" value={checked ? "true" : "false"} />
      <button
        aria-pressed={checked}
        aria-label={label}
        className={`rounded-full px-3 py-1 text-xs font-semibold ${checked ? "bg-ink-primary text-white" : "bg-white text-ink-muted"}`}
        onClick={(event) => {
          event.preventDefault();
          onChange(!checked);
        }}
        type="button"
      >
        {checked ? "已开启" : "已关闭"}
      </button>
    </label>
  );
}
