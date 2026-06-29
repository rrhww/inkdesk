# Workbook JSON Contract

## Contents

- [Top-level fields](#top-level-fields)
- [Events](#events)
- [Focus episode](#focus-episode)
- [Decision trace](#decision-trace)
- [Transfer challenge](#transfer-challenge)
- [Mastery](#mastery)
- [Complete example](#complete-example)

## Top-level fields

All fields below are required unless marked optional.

| Field | Type | Rule |
| --- | --- | --- |
| `title` | string | Human-readable workbook title |
| `topic` | string | Short description of the session topic |
| `date` | string | Prefer `YYYY-MM-DD` |
| `language` | string | Optional; defaults to `zh-CN` |
| `estimated_minutes` | integer | Positive integer |
| `stage` | string | `workbook` or `final` |
| `outcomes` | string array | At least one verified session outcome |
| `events` | object array | At least one event, exactly one selected |
| `focus` | object | Selected episode lesson |
| `checklist` | string array | Reusable future actions |
| `mastery` | object | Evidence-based mastery state |

Keep source code and logs out of the JSON unless a short escaped fragment is essential to the lesson. Prefer explanations of evidence.

## Events

Each event contains:

```json
{
  "id": "debug-race",
  "type": "debugging",
  "title": "排查搜索结果偶尔回退",
  "selected": true
}
```

Recommended `type` values are `debugging`, `requirements`, `design`, `implementation`, `refactoring`, and `review`. Other strings render as written.

## Focus episode

`focus` contains:

| Field | Type | Rule |
| --- | --- | --- |
| `title` | string | Transferable lesson title |
| `type` | string | Event type |
| `known_facts` | string array | Only facts available at the rewind point |
| `rewind` | object | Active-recall prompt |
| `trace` | object array | Evidence-labelled decision trace |
| `failed_attempts` | object array | Optional; informative or inefficient attempts |
| `principles` | object array | Causal models to retain |
| `transfer` | object | Near-transfer exercise |

`rewind` contains a `question` string and a non-empty `prompts` string array. Ask what to do, what to expect, and how each result changes the conclusion.

Each failed attempt contains `title` and `lesson`. Do not include a failure merely because it happened; include it when it changed the search space or teaches how to avoid low-information work.

Each principle contains `title` and `explanation`.

## Decision trace

Each trace item contains:

```json
{
  "label": "evidence",
  "step": "增加请求身份日志",
  "detail": "日志显示第二个请求先完成。",
  "outcome": "支持客户端竞态，排除服务端内容错误。"
}
```

Allowed labels:

- `evidence`: directly visible in conversation, commands, diffs, logs, or tests.
- `reconstruction`: a calibrated interpretation of visible actions.
- `recommendation`: a better path proposed after the event.

The renderer rejects other labels.

## Transfer challenge

`transfer` contains:

- `scenario`: change surface details while preserving the mechanism.
- `questions`: require a fresh diagnostic or design decision.
- `reference_answer`: concise reference path shown only after disclosure.

Do not create a recall question that can be answered by copying a sentence from the expert path.

## Mastery

```json
{
  "status": "exposed",
  "evidence": [],
  "next_review": "完成迁移练习后安排"
}
```

Allowed states are `exposed`, `explained`, `transferred`, and `independent`.

- `workbook` stage requires `exposed`.
- A `final` report above `exposed` requires at least one learner-produced evidence string.
- Agent-authored code and report generation are not learner evidence.
- `next_review` is optional.

## Complete example

```json
{
  "title": "从一次竞态 Bug 中学习",
  "topic": "异步搜索结果竞态",
  "date": "2026-06-19",
  "language": "zh-CN",
  "estimated_minutes": 3,
  "stage": "workbook",
  "outcomes": ["定位旧请求覆盖新请求的竞态条件"],
  "events": [
    {
      "id": "debug-race",
      "type": "debugging",
      "title": "排查搜索结果偶尔回退",
      "selected": true
    }
  ],
  "focus": {
    "title": "用证据区分缓存错误与请求竞态",
    "type": "debugging",
    "known_facts": ["单次搜索正确", "连续搜索偶尔回退"],
    "rewind": {
      "question": "下一步最有区分度的检查是什么？",
      "prompts": ["观察什么？", "不同结果如何改变判断？"]
    },
    "trace": [
      {
        "label": "evidence",
        "step": "记录请求身份",
        "detail": "旧请求在新请求之后提交状态。",
        "outcome": "支持响应竞态。"
      },
      {
        "label": "recommendation",
        "step": "改进路径",
        "detail": "控制响应完成顺序。",
        "outcome": "稳定复现并验证修复。"
      }
    ],
    "failed_attempts": [],
    "principles": [
      {
        "title": "完成顺序不等于发起顺序",
        "explanation": "共享状态需要显式提交权限。"
      }
    ],
    "transfer": {
      "scenario": "快速切换资料页时旧资料覆盖新资料。",
      "questions": ["如何证明？", "如何稳定测试？"],
      "reference_answer": "标记导航身份并控制响应顺序。"
    }
  },
  "checklist": ["记录发起、完成和提交顺序"],
  "mastery": {
    "status": "exposed",
    "evidence": [],
    "next_review": "完成迁移练习后安排"
  }
}
```
