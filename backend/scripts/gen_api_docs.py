# -*- coding: utf-8 -*-
"""从运行中的后端服务抓取 OpenAPI 规范，生成可传输的 Markdown API 文档。

用法:
    python scripts/gen_api_docs.py [--out docs/API文档.md] [--openapi-url http://127.0.0.1:8000/openapi.json]
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.request
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TYPE_NAMES = {
    "string": "string",
    "integer": "integer",
    "number": "number",
    "boolean": "boolean",
    "array": "array",
    "object": "object",
    "file": "file(binary)",
}


def resolve_ref(ref: str, components: Dict[str, Any]) -> Tuple[str, Optional[Dict[str, Any]]]:
    """解析 $ref -> (schema 名称, schema 定义)。"""
    name = ref.split("/")[-1]
    return name, components.get("schemas", {}).get(name)


def schema_summary(schema: Any, components: Dict[str, Any], depth: int = 0) -> str:
    """把一个 schema 渲染为紧凑的类型描述。"""
    if schema is None:
        return "any"
    if "$ref" in schema:
        return schema["$ref"].split("/")[-1]
    if "anyOf" in schema or "oneOf" in schema:
        keys = "anyOf" if "anyOf" in schema else "oneOf"
        return " | ".join(schema_summary(s, components, depth) for s in schema.get(keys, []))
    if schema.get("type") == "array":
        return f"array[{schema_summary(schema.get('items'), components, depth)}]"
    t = TYPE_NAMES.get(schema.get("type", ""), schema.get("type", "any"))
    fmt = schema.get("format")
    if fmt:
        return f"{t}({fmt})"
    if "enum" in schema:
        return f"{t} 枚举 {schema['enum']}"
    return t


def schema_fields(schema: Any, components: Dict[str, Any], depth: int = 0) -> List[str]:
    """展开 schema 的属性为 Markdown 行。"""
    lines: List[str] = []
    if schema is None:
        return lines
    if "$ref" in schema:
        _, target = resolve_ref(schema["$ref"], components)
        if target:
            return schema_fields(target, components, depth)
    if "allOf" in schema:
        for part in schema.get("allOf", []):
            lines.extend(schema_fields(part, components, depth))
        return lines
    props = schema.get("properties")
    if not props:
        return lines
    required = set(schema.get("required", []))
    indent = "  " * depth
    for name, ps in props.items():
        desc = (ps.get("description") or "").replace("\n", " ")
        if ps.get("$ref"):
            ref_name, target = resolve_ref(ps["$ref"], components)
            summary = ref_name
            _ = target
        else:
            summary = schema_summary(ps, components, depth)
        req = "必填" if name in required else "可选"
        lines.append(f"{indent}- `{name}`：{summary}，{req}。{desc}".rstrip())
        sub = ps.get("items") or ps
        if sub.get("properties") and depth < 4:
            lines.extend(schema_fields(sub, components, depth + 1))
        elif sub.get("$ref"):
            _, target = resolve_ref(sub["$ref"], components)
            if target and target.get("properties"):
                lines.extend(schema_fields(target, components, depth + 1))
    return lines


def op_summary(op: Dict[str, Any], method: str, path: str, components: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    summary = op.get("summary") or op.get("operationId") or ""
    desc = (op.get("description") or "").strip()
    lines.append(f"### {method.upper()} `{path}` — {summary}")
    if desc:
        lines.append("")
        lines.append(desc)
    lines.append("")

    params = op.get("parameters", [])
    if params:
        lines.append("**请求参数**")
        lines.append("")
        for p in params:
            loc = {"path": "路径", "query": "查询", "header": "头"}.get(p.get("in"), p.get("in"))
            sch = p.get("schema", {})
            req = "必填" if p.get("required") else "可选"
            desc = (p.get("description") or "").replace("\n", " ")
            lines.append(f"- `{p['name']}`（{loc}，{req}）：{schema_summary(sch, components)}。{desc}".rstrip())
        lines.append("")

    rb = op.get("requestBody")
    if rb:
        content = rb.get("content", {})
        for ctype, cval in content.items():
            schema = cval.get("schema")
            if schema:
                lines.append("**请求体**")
                lines.append("")
                if rb.get("required"):
                    lines.append("> 必填")
                    lines.append("")
                if ctype != "application/json":
                    lines.append(f"> Content-Type: `{ctype}`")
                    lines.append("")
                fields = schema_fields(schema, components)
                if fields:
                    lines.extend(fields)
                else:
                    lines.append(f"- 结构：`{schema_summary(schema, components)}`")
                lines.append("")

    lines.append("**响应**")
    lines.append("")
    responses = op.get("responses", {})
    if not responses:
        lines.append("- 无")
    for code, resp in sorted(responses.items()):
        desc = resp.get("description", "")
        content = resp.get("content", {})
        detail = ""
        for ctype, cval in content.items():
            schema = cval.get("schema")
            if schema:
                detail = schema_summary(schema, components)
                break
        extra = f" — `{detail}`" if detail else ""
        lines.append(f"- `{code}`：{desc}{extra}")
    lines.append("")
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(description="生成可传输的 Markdown API 文档")
    parser.add_argument("--openapi-url", default="http://127.0.0.1:8000/openapi.json")
    parser.add_argument("--out", default=os.path.join(PROJECT_ROOT, "docs", "API_Reference.md"))
    args = parser.parse_args()

    print(f"fetching {args.openapi_url} ...")
    with urllib.request.urlopen(args.openapi_url, timeout=10) as resp:
        spec: Dict[str, Any] = json.load(resp)

    info: Dict[str, Any] = spec.get("info", {})
    components: Dict[str, Any] = spec.get("components", {})
    tags: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = defaultdict(list)
    paths: Dict[str, Any] = spec.get("paths", {})
    for path, item in paths.items():
        for method, op in item.items():
            if method not in ("get", "post", "put", "patch", "delete"):
                continue
            tag = (op.get("tags") or ["默认"])[0]
            tags[tag].append((path, method, op))

    lines: List[str] = []
    lines.append(f"# {info.get('title', 'API')} — API 接口文档")
    lines.append("")
    lines.append(f"> 版本：`{info.get('version', '')}` | 接口总数：{sum(len(v) for v in tags.values())} | 生成时间：")
    lines.append("")
    lines.append("> 约定：业务错误统一返回 **HTTP 200**，错误码在响应体 `code` 字段（如 40100 未认证 / 40300 禁止 / 40400 未找到 / 40900 冲突 / 42200 参数错误）。")
    lines.append("")
    lines.append("## 目录")
    lines.append("")
    for tag in sorted(tags):
        lines.append(f"- [{tag}](#{tag.lower()})")
    lines.append("")

    # 通用组件（公共 schema）
    schema_names = sorted(components.get("schemas", {}).keys())
    lines.append("## 通用数据模型")
    lines.append("")
    for name in schema_names:
        schema = components["schemas"][name]
        desc = (schema.get("description") or "").strip()
        lines.append(f"### `{name}`")
        if desc:
            lines.append("")
            lines.append(desc)
        lines.append("")
        fields = schema_fields(schema, components)
        if fields:
            lines.extend(fields)
        else:
            lines.append(f"- 类型：`{schema_summary(schema, components)}`")
        lines.append("")
    lines.append("---")
    lines.append("")

    for tag in sorted(tags):
        lines.append(f"## {tag}")
        lines.append("")
        for path, method, op in sorted(tags[tag], key=lambda x: x[1]):
            lines.extend(op_summary(op, method, path, components))
        lines.append("---")
        lines.append("")

    # 服务级 schema 引用：补一份所有 schema 索引
    content = "\n".join(lines)
    # 写入日期
    import datetime
    content = content.replace("生成时间：", f"生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M}")
    out = args.out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"written {out} ({len(content)} chars, {sum(len(v) for v in tags.values())} endpoints)")


if __name__ == "__main__":
    main()
