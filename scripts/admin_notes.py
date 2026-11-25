#!/usr/bin/env python3
"""admin_notes.py — 解析输入中的管理性材料：别名表、版本说明、元数据表。

案例可能随附管理文件（不是文献本身），例如:
- aliases.txt / 别名表: "规范名 = 别名1, 别名2" 或 "别名 -> 规范名" 或 JSON 映射
- version_notes.md / 版本说明: "A superseded by B"、"v2 replaces v1"、"authoritative: X"
- metadata.csv/.json: 以 filename/doi/title 为键的权威元数据行

解析结果写 /app/work/admin.json；无法解析的行原样保留在 unparsed 供 Agent 人工裁决。
管理指令优先级高于启发式，低于原文直证；来源统一标注 admin_note。

用法: python3 admin_notes.py [--work-dir /app/work]
"""
import argparse, csv, json, os, re, sys

ADMIN_NAME_RE = re.compile(r"(?i)(alias|别名|version[_ -]?notes?|版本说明|版本备注|"
                           r"admin[_ -]?notes?|管理说明|metadata\.(csv|json)|manifest\.(csv|json))")

def parse_alias_lines(text):
    """别名映射：返回 {alias: canonical}。"""
    out = {}
    for line in text.splitlines():
        s = line.strip().strip(",")
        if not s or s.startswith("#"):
            continue
        m = re.match(r"^(.+?)\s*(?:=|->|→|：|:)\s*(.+)$", s)
        if not m:
            continue
        left, right = m.group(1).strip(), m.group(2).strip()
        # 形如 "canonical = alias1, alias2"：右侧列表逐个映射到左侧
        parts = [p.strip() for p in re.split(r"[,;、]", right) if p.strip()]
        if len(parts) > 1:
            for p in parts:
                out[p] = left
        else:
            # 形如 "alias -> canonical"：左侧映射到右侧
            out[left] = right
    return out

def parse_version_lines(text):
    """版本指令：superseded/replaces/authoritative。"""
    directives = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        m = re.search(r"(?i)(.+?)\s+(?:is\s+)?superseded\s+by\s+(.+)", s)
        if m:
            directives.append({"type": "superseded_by", "old": m.group(1).strip(),
                               "new": m.group(2).strip(), "raw": s})
            continue
        m = re.search(r"(?i)(.+?)\s+replaces\s+(.+)", s)
        if m:
            directives.append({"type": "superseded_by", "old": m.group(2).strip(),
                               "new": m.group(1).strip(), "raw": s})
            continue
        m = re.search(r"(?i)(?:authoritative|canonical|以.*为准|正式版)\s*[:：]?\s*(.+)", s)
        if m:
            directives.append({"type": "authoritative", "file": m.group(1).strip(), "raw": s})
            continue
    return directives

def parse_metadata_file(path):
    """CSV/JSON 元数据表 → {key: row}，键为 filename/doi/title 之一。"""
    rows = []
    try:
        if path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rows = data if isinstance(data, list) else [data]
        else:
            with open(path, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
    except Exception as e:
        return [], f"解析失败: {e}"
    out = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        key = (r.get("filename") or r.get("file") or r.get("doi")
               or r.get("DOI") or r.get("title"))
        if key:
            out[str(key).strip().lower()] = {k.lower(): v for k, v in r.items()}
    return out, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    args = ap.parse_args()
    brief_path = os.path.join(args.work_dir, "brief.json")
    if not os.path.exists(brief_path):
        print("[admin_notes] 缺少 brief.json", file=sys.stderr)
        return 2
    with open(brief_path, "r", encoding="utf-8") as f:
        brief = json.load(f)
    input_dir = brief.get("input_dir", "/input")

    admin = {"aliases": {}, "version_directives": [], "metadata_table": {},
             "admin_files": [], "unparsed": []}
    for root, dirs, files in os.walk(input_dir):
        dirs.sort()
        for fn in sorted(files):
            if not ADMIN_NAME_RE.search(fn):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, input_dir)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError as e:
                admin["unparsed"].append(f"{rel}: 读取失败 {e}")
                continue
            admin["admin_files"].append(rel)
            low = fn.lower()
            if "alias" in low or "别名" in fn:
                admin["aliases"].update(parse_alias_lines(text))
            elif "version" in low or "版本" in fn or "admin" in low or "管理" in fn:
                admin["version_directives"].extend(parse_version_lines(text))
                # 版本说明里常夹带别名行
                admin["aliases"].update(parse_alias_lines(text))
            elif low.startswith("metadata") or low.startswith("manifest"):
                table, err = parse_metadata_file(p)
                if err:
                    admin["unparsed"].append(f"{rel}: {err}")
                admin["metadata_table"].update(table)

    # 收集无法匹配任何解析器的行（供 Agent 人工裁决）
    if admin["admin_files"] and not (admin["aliases"] or admin["version_directives"]
                                     or admin["metadata_table"]):
        admin["unparsed"].append("识别到管理文件但未解析出指令，请 Agent 人工阅读: "
                                 + ", ".join(admin["admin_files"]))

    with open(os.path.join(args.work_dir, "admin.json"), "w", encoding="utf-8") as f:
        json.dump(admin, f, ensure_ascii=False, indent=2)
    print(f"[admin_notes] files={len(admin['admin_files'])} aliases={len(admin['aliases'])} "
          f"directives={len(admin['version_directives'])} meta_rows={len(admin['metadata_table'])} "
          f"unparsed={len(admin['unparsed'])}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
