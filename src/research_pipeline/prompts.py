from __future__ import annotations

from pathlib import Path
import yaml


DEFAULT_SINGLE_PAPER_PROMPT = """你是论文分析助手。请基于提供的单篇论文上下文，提炼结构化摘要并返回 JSON。\n
只返回合法 JSON，格式如下：\n
{\n  \"paper_summary\": {\n    \"paper_id\": \"...\",\n    \"title\": \"...\",\n    \"tasks\": [\"...\"],\n    \"data_sources\": [\"...\"],\n    \"evaluation\": [\"...\"],\n    \"safety_ethics\": [\"...\"],\n    \"deployment\": [\"...\"],\n    \"limitations\": [\"...\"],\n    \"evidence\": [\n      {\"chunk_id\": \"...\"}\n    ]\n  }\n}\n
规则：\n- 仅使用提供的上下文，不得编造。\n- 所有文本使用简体中文。\n- 每个字段尽量给出 1-3 条要点。\n- evidence 中 chunk_id 必须来自上下文。\n- 仅返回 chunk_id，不要返回 quote；quote 将由系统从原文 chunk 自动提取英文原句。\n\n输入信息：\n- 主题: {topic}\n- 问题列表: {questions}\n- 论文ID: {paper_id}\n- 论文标题: {paper_title}\n- 上下文:\n{context_chunks}\n"""

DEFAULT_FINAL_TOPIC_PROMPT = """你是中文科研综述助手。请根据多篇论文的上下文与单篇摘要，生成主题级结论并返回 JSON。\n
只返回合法 JSON，格式如下：\n
{\n  \"findings\": [\n    {\n      \"claim\": \"...\",\n      \"evidence\": [\n        {\"chunk_id\": \"...\"}\n      ]\n    }\n  ],\n  \"paper_map\": {\n    \"概览\": [\"paper_id\"],\n    \"应用\": [\"paper_id\"],\n    \"评估\": [\"paper_id\"],\n    \"安全与伦理\": [\"paper_id\"],\n    \"部署\": [\"paper_id\"],\n    \"局限与开放问题\": [\"paper_id\"]\n  }\n}\n
规则：\n- 仅使用给定内容，不得编造。\n- 所有 claim 使用简体中文。\n- 至少输出 {min_findings} 条结论。\n- evidence 的 chunk_id 必须精确匹配提供的上下文。\n- 仅返回 chunk_id，不要返回 quote；quote 将由系统从原文 chunk 自动提取英文原句。\n- 每条结论至少包含 1 条有效 evidence。\n- 如果上轮校验失败，请根据重试信息修正：{retry_notes}\n\n输入信息：\n- 主题: {topic}\n- 问题列表: {questions}\n- 单篇摘要（可为空）:\n{single_paper_summaries}\n- 上下文:\n{context_chunks}\n"""


def load_prompt_templates(path: Path) -> tuple[str, str]:
    if not path.exists():
        return DEFAULT_SINGLE_PAPER_PROMPT, DEFAULT_FINAL_TOPIC_PROMPT

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    single_prompt = str(data.get("single_paper_summary_prompt") or DEFAULT_SINGLE_PAPER_PROMPT)
    final_prompt = str(data.get("final_topic_summary_prompt") or DEFAULT_FINAL_TOPIC_PROMPT)
    return single_prompt, final_prompt
