#!/usr/bin/env python3
"""kb_index.py — 建立可检索索引：按页提取文本、切块、倒排索引（纯标准库）。

覆盖"index 操作"类任务：整理后对 library/ 内全部文本可提取文件建索引，
每块携带 文件路径 + 页码 + 块号，支持复核回链。

用法: python3 kb_index.py [--work-dir /app/work] [--output-dir /app/output]
输出: /app/output/index/chunks.jsonl, /app/output/index/inverted.json, /app/output/index/stats.json
"""
import argparse, json, math, os, re, subprocess, sys
from collections import defaultdict

def run(cmd, timeout=120):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception:
        return -1, "", ""

def page_texts(pdf_path, max_pages=80):
    """逐页提取 PDF 文本（限前 max_pages 页）。"""
    rc, out, _ = run(["pdfinfo", pdf_path])
    pages = 0
    if rc == 0:
        m = re.search(r"^Pages:\s*(\d+)", out, re.M)
        if m:
            pages = min(int(m.group(1)), max_pages)
    if pages == 0:
        return []
    texts = []
    for n in range(1, pages + 1):
        rc, out, _ = run(["pdftotext", "-f", str(n), "-l", str(n), pdf_path, "-"])
        texts.append(out if rc == 0 else "")
    return texts

def tokenize(text):
    """拉丁词（小写）+ CJK 二元组 + CJK 单字兜底。"""
    text = text.lower()
    toks = re.findall(r"[a-z0-9][a-z0-9\-']+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    toks += [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    toks += cjk
    return toks

STOP = set("the a an and or of to in on for with is are was were be been by at from as it its this that 的 了 和 是 在 与 及 或 为 对 由".split())

def segment(text, size=600, overlap=120):
    """按字符窗口切块，尽量落在段落边界。"""
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    chunks, i = [], 0
    while i < len(text):
        j = min(i + size, len(text))
        if j < len(text):
            cut = text.rfind("\n", i + size // 2, j)
            if cut > i:
                j = cut
        chunks.append(text[i:j].strip())
        i = j - overlap if j < len(text) else j
        if i < 0:
            i = 0
    return [c for c in chunks if len(c) >= 40]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    args = ap.parse_args()

    arep_path = os.path.join(args.work_dir, "apply_report.json")
    if not os.path.exists(arep_path):
        print("[kb_index] 缺少 apply_report.json，请先运行 apply.py", file=sys.stderr)
        return 2
    with open(arep_path, "r", encoding="utf-8") as f:
        arep = json.load(f)

    idx_dir = os.path.join(args.output_dir, "index")
    os.makedirs(idx_dir, exist_ok=True)
    chunks = []
    for item in arep.get("items", []):
        if item["action"] != "place" or not item.get("target"):
            continue
        dst = os.path.join(args.output_dir, item["target"])
        if not os.path.exists(dst):
            continue
        base = os.path.basename(dst).lower()
        texts = []
        if base.endswith(".pdf"):
            texts = page_texts(dst)
        elif base.endswith((".txt", ".md", ".csv", ".bib", ".ris")):
            try:
                with open(dst, "r", encoding="utf-8", errors="replace") as f:
                    texts = [f.read()]
            except OSError:
                texts = []
        for pno, ptext in enumerate(texts, 1):
            for cno, chunk in enumerate(segment(ptext), 1):
                chunks.append({
                    "chunk_id": f"{item['target']}#p{pno}c{cno}",
                    "file": item["target"], "page": pno, "chunk": cno,
                    "text": chunk,
                })

    # 倒排索引: term -> {chunk_id: tf}
    inverted = defaultdict(dict)
    doc_len = {}
    for c in chunks:
        toks = [t for t in tokenize(c["text"]) if t not in STOP]
        doc_len[c["chunk_id"]] = max(len(toks), 1)
        tf = defaultdict(int)
        for t in toks:
            tf[t] += 1
        for t, n in tf.items():
            inverted[t][c["chunk_id"]] = n

    with open(os.path.join(idx_dir, "chunks.jsonl"), "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(os.path.join(idx_dir, "inverted.json"), "w", encoding="utf-8") as f:
        json.dump({"inverted": inverted, "doc_len": doc_len}, f, ensure_ascii=False)
    stats = {"chunks": len(chunks),
             "files_indexed": len({c["file"] for c in chunks}),
             "terms": len(inverted)}
    with open(os.path.join(idx_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"[kb_index] chunks={stats['chunks']} files={stats['files_indexed']} terms={stats['terms']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
