"""Render an interactive learning workbook from structured session data."""

from __future__ import annotations

import argparse
import copy
from html import escape
import json
from pathlib import Path
import re
import sys
from typing import Any


SKILL_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = SKILL_DIR / "assets" / "learning-workbook-template.html"
TRACE_LABELS = {
    "evidence": ("会话证据", "badge-evidence"),
    "reconstruction": ("合理重建", "badge-reconstruction"),
    "recommendation": ("改进建议", "badge-recommendation"),
}
MASTERY_LABELS = {
    "exposed": "接触过",
    "explained": "能够解释",
    "transferred": "能够迁移",
    "independent": "能够独立应用",
}
EVENT_LABELS = {
    "debugging": "调试",
    "requirements": "需求分析",
    "design": "方案设计",
    "implementation": "功能实现",
    "refactoring": "重构",
    "review": "代码审查",
}


def load_workbook(path: str | Path) -> dict[str, Any]:
    input_path = Path(path)
    try:
        data = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"Workbook input does not exist: {input_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError("Workbook root must be a JSON object")
    return data


def _required(mapping: dict[str, Any], key: str, path: str, expected: type) -> Any:
    value = mapping.get(key)
    full_path = f"{path}.{key}" if path else key
    if not isinstance(value, expected) or (expected in (str, list, dict) and not value):
        raise ValueError(f"{full_path} is required and must be a non-empty {expected.__name__}")
    return value


def _string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{path} must be a non-empty list of strings")
    return value


def validate_workbook(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Workbook root must be an object")
    validated = copy.deepcopy(data)

    for key in ("title", "topic", "date", "stage"):
        _required(validated, key, "", str)
    if validated["stage"] not in {"workbook", "final"}:
        raise ValueError("stage must be workbook or final")
    minutes = validated.get("estimated_minutes")
    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes < 1:
        raise ValueError("estimated_minutes must be a positive integer")
    _string_list(validated.get("outcomes"), "outcomes")
    _string_list(validated.get("checklist"), "checklist")

    events = _required(validated, "events", "", list)
    selected = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f"events.{index} must be an object")
        for key in ("id", "type", "title"):
            _required(event, key, f"events.{index}", str)
        if not isinstance(event.get("selected"), bool):
            raise ValueError(f"events.{index}.selected must be a boolean")
        selected += int(event["selected"])
    if selected != 1:
        raise ValueError("events must contain exactly one selected episode")

    focus = _required(validated, "focus", "", dict)
    for key in ("title", "type"):
        _required(focus, key, "focus", str)
    _string_list(focus.get("known_facts"), "focus.known_facts")
    rewind = _required(focus, "rewind", "focus", dict)
    _required(rewind, "question", "focus.rewind", str)
    _string_list(rewind.get("prompts"), "focus.rewind.prompts")

    trace = _required(focus, "trace", "focus", list)
    for index, item in enumerate(trace):
        if not isinstance(item, dict):
            raise ValueError(f"focus.trace.{index} must be an object")
        label = _required(item, "label", f"focus.trace.{index}", str)
        if label not in TRACE_LABELS:
            raise ValueError("trace label must be one of evidence, reconstruction, recommendation")
        for key in ("step", "detail", "outcome"):
            _required(item, key, f"focus.trace.{index}", str)

    failed_attempts = focus.get("failed_attempts", [])
    if not isinstance(failed_attempts, list):
        raise ValueError("focus.failed_attempts must be a list")
    for index, item in enumerate(failed_attempts):
        if not isinstance(item, dict):
            raise ValueError(f"focus.failed_attempts.{index} must be an object")
        for key in ("title", "lesson"):
            _required(item, key, f"focus.failed_attempts.{index}", str)

    principles = _required(focus, "principles", "focus", list)
    for index, item in enumerate(principles):
        if not isinstance(item, dict):
            raise ValueError(f"focus.principles.{index} must be an object")
        for key in ("title", "explanation"):
            _required(item, key, f"focus.principles.{index}", str)

    transfer = _required(focus, "transfer", "focus", dict)
    _required(transfer, "scenario", "focus.transfer", str)
    _string_list(transfer.get("questions"), "focus.transfer.questions")
    _required(transfer, "reference_answer", "focus.transfer", str)

    mastery = _required(validated, "mastery", "", dict)
    status = _required(mastery, "status", "mastery", str)
    if status not in MASTERY_LABELS:
        raise ValueError(f"mastery.status must be one of {', '.join(MASTERY_LABELS)}")
    evidence = mastery.get("evidence")
    if not isinstance(evidence, list) or any(not isinstance(item, str) or not item.strip() for item in evidence):
        raise ValueError("mastery.evidence must be a list of strings")
    if validated["stage"] == "workbook" and status != "exposed":
        raise ValueError("workbook stage must use exposed mastery status")
    if validated["stage"] == "final" and status != "exposed" and not evidence:
        raise ValueError("final mastery above exposed requires learner evidence")

    language = validated.get("language", "zh-CN")
    if not isinstance(language, str) or not language.strip():
        raise ValueError("language must be a non-empty string")
    validated["language"] = language
    mastery.setdefault("next_review", "完成练习后安排")
    return validated


def _text(value: Any) -> str:
    return escape(str(value), quote=True)


def _list(items: list[str], class_name: str = "") -> str:
    class_attr = f' class="{class_name}"' if class_name else ""
    return f"<ul{class_attr}>" + "".join(f"<li>{_text(item)}</li>" for item in items) + "</ul>"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "session-learning"


def _render_events(events: list[dict[str, Any]]) -> str:
    cards = []
    for event in events:
        event_type = EVENT_LABELS.get(event["type"], event["type"])
        current = "true" if event["selected"] else "false"
        cards.append(
            f'<article class="event-card" aria-current="{current}">'
            f"<h3>{_text(event['title'])}</h3><p>{_text(event_type)}</p></article>"
        )
    return "".join(cards)


def _render_trace(trace: list[dict[str, str]]) -> str:
    items = []
    for item in trace:
        label_text, label_class = TRACE_LABELS[item["label"]]
        items.append(
            '<article class="trace-item">'
            f'<span class="badge {label_class}">{label_text}</span>'
            f"<h3>{_text(item['step'])}</h3>"
            f"<p>{_text(item['detail'])}</p>"
            f'<p class="outcome"><strong>这一步改变了什么：</strong> {_text(item["outcome"])}</p>'
            "</article>"
        )
    return "".join(items)


def _render_content(data: dict[str, Any]) -> str:
    focus = data["focus"]
    rewind = focus["rewind"]
    transfer = focus["transfer"]
    mastery = data["mastery"]
    mastery_evidence = mastery["evidence"]
    mastery_note = "；".join(mastery_evidence) if mastery_evidence else "尚未验证掌握"

    failed_html = ""
    if focus["failed_attempts"]:
        attempts = "".join(
            f'<div class="callout"><h3>{_text(item["title"])}</h3><p>{_text(item["lesson"])}</p></div>'
            for item in focus["failed_attempts"]
        )
        failed_html = f"<h3>有价值的失败与低效步骤</h3>{attempts}"

    principles = "".join(
        f'<article class="principle"><h3>{_text(item["title"])}</h3><p>{_text(item["explanation"])}</p></article>'
        for item in focus["principles"]
    )
    stage_text = "学习工作簿" if data["stage"] == "workbook" else "学习报告"

    return f"""
<a class="skip-link" href="#main-content">跳到主要内容</a>
<header class="hero shell">
  <p class="eyebrow">Learn From Session · {stage_text}</p>
  <h1>{_text(data['title'])}</h1>
  <p class="lede">{_text(data['topic'])}</p>
  <div class="meta" aria-label="报告信息">
    <span class="chip">{_text(data['date'])}</span>
    <span class="chip">约 {_text(data['estimated_minutes'])} 分钟</span>
    <span class="chip">{_text(MASTERY_LABELS[mastery['status']])}</span>
  </div>
</header>
<main id="main-content" class="shell">
  <section aria-labelledby="outcomes-title">
    <p class="eyebrow">Session outcome</p>
    <h2 id="outcomes-title">本轮完成了什么</h2>
    {_list(data['outcomes'])}
  </section>

  <section class="quiet" aria-labelledby="events-title">
    <p class="eyebrow">Episode map</p>
    <h2 id="events-title">会话事件地图</h2>
    <div class="event-grid">{_render_events(data['events'])}</div>
  </section>

  <section aria-labelledby="focus-title">
    <p class="eyebrow">Focus episode · {_text(EVENT_LABELS.get(focus['type'], focus['type']))}</p>
    <h2 id="focus-title">{_text(focus['title'])}</h2>
    <h3>回到当时：你已经知道什么</h3>
    {_list(focus['known_facts'], 'fact-list')}
  </section>

  <section class="rewind" aria-labelledby="rewind-title">
    <p class="eyebrow">Pause and predict</p>
    <h2 id="rewind-title">场景倒带</h2>
    <p class="question">{_text(rewind['question'])}</p>
    {_list(rewind['prompts'], 'prompt-list')}
    <label for="rewind-answer">先写下你的判断</label>
    <textarea id="rewind-answer" data-learning-answer spellcheck="true" placeholder="写下下一步、预期结果，以及不同结果会如何改变你的判断。"></textarea>
    <noscript><p class="no-script-note">JavaScript 已关闭。你仍可作答并手动复制文本，下面的折叠内容也可以正常展开。</p></noscript>
    <details>
      <summary>完成作答后，展开专家路径</summary>
      <div class="trace">{_render_trace(focus['trace'])}</div>
      {failed_html}
    </details>
  </section>

  <section aria-labelledby="principles-title">
    <p class="eyebrow">Mental model</p>
    <h2 id="principles-title">带走这个底层模型</h2>
    <div class="principle-grid">{principles}</div>
  </section>

  <section aria-labelledby="transfer-title">
    <p class="eyebrow">Near transfer</p>
    <h2 id="transfer-title">换一个场景，再做一次判断</h2>
    <p>{_text(transfer['scenario'])}</p>
    {_list(transfer['questions'], 'prompt-list')}
    <label for="transfer-answer">你的迁移答案</label>
    <textarea id="transfer-answer" data-learning-answer spellcheck="true" placeholder="不要复述原案例，说明你会如何验证和决策。"></textarea>
    <details>
      <summary>作答后展开参考思路</summary>
      <p>{_text(transfer['reference_answer'])}</p>
    </details>
    <button type="button" id="copy-answers">复制我的回答</button>
    <p id="copy-status" class="status" role="status" aria-live="polite"></p>
  </section>

  <section class="quiet" aria-labelledby="checklist-title">
    <p class="eyebrow">Reusable checklist</p>
    <h2 id="checklist-title">下次可以直接使用</h2>
    {_list(data['checklist'], 'checklist')}
  </section>

  <section aria-labelledby="mastery-title">
    <p class="eyebrow">Mastery evidence</p>
    <h2 id="mastery-title">当前掌握证据</h2>
    <div class="mastery">
      <span class="mastery-mark" aria-hidden="true"></span>
      <div><h3>{_text(MASTERY_LABELS[mastery['status']])}</h3><p>{_text(mastery_note)}</p><p><strong>建议复习：</strong> {_text(mastery['next_review'])}</p></div>
    </div>
  </section>
</main>
<footer class="shell">由 Learn From Session 根据当前会话的可见证据生成。合理重建与改进建议不等同于原会话中的明确推理。</footer>
""".strip()


def render_workbook(data: dict[str, Any], template_path: str | Path | None = None) -> str:
    validated = validate_workbook(data)
    path = Path(template_path) if template_path is not None else DEFAULT_TEMPLATE
    try:
        template = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ValueError(f"HTML template does not exist: {path}") from error

    replacements = {
        "{{LANG}}": _text(validated["language"]),
        "{{PAGE_TITLE}}": _text(validated["title"]),
        "{{REPORT_KEY}}": _text(f"{validated['date']}-{_slug(validated['topic'])}"),
        "{{CONTENT}}": _render_content(validated),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    unresolved = re.findall(r"\{\{[A-Z_]+\}\}", rendered)
    if unresolved:
        raise ValueError(f"Unresolved template placeholders: {', '.join(sorted(set(unresolved)))}")
    return rendered


def write_workbook(
    input_path: str | Path,
    output_path: str | Path,
    template_path: str | Path | None = None,
) -> Path:
    data = load_workbook(input_path)
    rendered = render_workbook(data, template_path=template_path)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8", newline="\n")
    return destination


def _default_output(data: dict[str, Any]) -> Path:
    return Path.cwd() / "learning-reviews" / f"{data['date']}-{_slug(data['topic'])}.html"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to workbook JSON")
    parser.add_argument("--output", type=Path, help="Destination HTML path")
    parser.add_argument("--template", type=Path, help="Optional template override")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        data = load_workbook(args.input)
        output = args.output or _default_output(data)
        rendered = render_workbook(data, template_path=args.template)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8", newline="\n")
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(f"Created learning workbook: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
