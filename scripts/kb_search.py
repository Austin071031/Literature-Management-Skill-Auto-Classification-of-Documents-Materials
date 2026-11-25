#!/usr/bin/env python3
"""kb_search.py — 索引检索：BM25 风格打分 + 短语邻接奖励，中英文混合。

用法:
  python3 kb_search.py --output-dir /app/output --query "催化 转化率" [--topk 8]
  python3 kb_search.py --output-dir /app/output --questions /app/work/questions.json [--topk 8]
questions.json: [{"id":"q1","question":"...","type":"search|question"}]
输出: 单查询打印 JSON；批量写 /app/work/search_results.json
"""
import argparse, json, math, os, re, sys
from collections import defaultdict

def tokenize(text):
    text = text.lower()
    toks = re.findall(r"[a-z0-9][a-z0-9\-']+", text)
    cjk = re.findall(r"[\u4e00-\u9fff]", text)
    toks += [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    toks += cjk
    return toks

STOP = set("the a an and or of to in on for with is are was were be been by at from as it its this that 的 了 和 是 在 与 及 或 为 对 由 什么 哪些 哪篇 请 问 列出 找出".split())

# 中英双语领域同义词扩展：解决中文提问与英文文献的词表鸿沟。
# 键为规范词，值为同义/对译词集合（双向展开）。
SYNONYMS = {
    "perovskite": {"钙钛矿"},
    "photocatalysis": {"光催化", "photocatalytic"},
    "catalysis": {"催化", "catalyst", "catalytic", "催化剂"},
    "battery": {"电池"},
    "electrolyte": {"电解液", "电解质"},
    "superconductivity": {"超导", "superconductor", "superconducting"},
    "quantum": {"量子"},
    "machine learning": {"机器学习", "ml"},
    "deep learning": {"深度学习"},
    "neural network": {"神经网络"},
    "density functional theory": {"密度泛函", "dft"},
    "molecular dynamics": {"分子动力学", "md"},
    "first-principles": {"第一性原理", "ab initio"},
    "high-throughput screening": {"高通量筛选", "高通量"},
    "phase transition": {"相变"},
    "band structure": {"能带"},
    "crystal structure": {"晶体结构"},
    "bayesian optimization": {"贝叶斯优化", "贝叶斯"},
    "defect": {"缺陷"},
    "interface": {"界面"},
    "dataset": {"数据集", "数据库"},
    "lithium-ion": {"锂离子", "锂电"},
    "screening": {"筛选"},
    "optimization": {"优化"},
    "review": {"综述"},
    "thesis": {"学位论文", "dissertation"},
    "preprint": {"预印本"},
}

def expand_query(tokens, raw_query=""):
    """对查询词做双向同义展开（在原始查询串上匹配，避免分词切断词）。"""
    raw = (raw_query or "").lower()
    extra = set()
    for canon, syns in SYNONYMS.items():
        group = {canon} | syns
        if any(g in raw or g in tokens for g in group):
            extra |= {t for t in group if t not in tokens}
    return tokens + sorted(extra)

def load_index(output_dir):
    idx_dir = os.path.join(output_dir, "index")
    with open(os.path.join(idx_dir, "inverted.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    chunks = {}
    with open(os.path.join(idx_dir, "chunks.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            chunks[c["chunk_id"]] = c
    return data["inverted"], data["doc_len"], chunks

def search(query, inverted, doc_len, chunks, topk=8, k1=1.5, b=0.75):
    base_toks = [t for t in tokenize(query) if t not in STOP]
    if not base_toks:
        return []
    qtoks = expand_query(base_toks, raw_query=query)
    base_set = set(base_toks)
    n_docs = max(len(doc_len), 1)
    avgdl = sum(doc_len.values()) / n_docs
    scores = defaultdict(float)
    for t in set(qtoks):
        postings = inverted.get(t)
        if not postings:
            continue
        idf = math.log(1 + (n_docs - len(postings) + 0.5) / (len(postings) + 0.5))
        if t not in base_set:
            idf *= 0.7  # 扩展词降权，原词优先
        for cid, tf in postings.items():
            dl = doc_len.get(cid, 1)
            scores[cid] += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    # 短语奖励：连续查询词在块文本中相邻出现
    qjoined = "".join(t for t in tokenize(query) if t not in STOP)
    for cid in list(scores):
        txt = chunks[cid]["text"].lower().replace(" ", "")
        if qjoined and qjoined in txt:
            scores[cid] *= 1.5
    ranked = sorted(scores.items(), key=lambda x: -x[1])[:topk]
    out = []
    for cid, sc in ranked:
        c = chunks[cid]
        out.append({
            "chunk_id": cid, "score": round(sc, 3),
            "file": c["file"], "page": c["page"], "chunk": c["chunk"],
            "excerpt": c["text"][:240],
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", default="/app/output")
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--query", default=None)
    ap.add_argument("--questions", default=None)
    ap.add_argument("--topk", type=int, default=8)
    args = ap.parse_args()
    inverted, doc_len, chunks = load_index(args.output_dir)

    if args.questions:
        with open(args.questions, "r", encoding="utf-8") as f:
            qs = json.load(f)
        results = []
        for q in qs:
            hits = search(q["question"], inverted, doc_len, chunks, args.topk)
            results.append({"id": q.get("id"), "question": q["question"], "hits": hits})
            print(f"[kb_search] {q.get('id')}: {len(hits)} hits")
        with open(os.path.join(args.work_dir, "search_results.json"), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
    elif args.query:
        hits = search(args.query, inverted, doc_len, chunks, args.topk)
        print(json.dumps(hits, ensure_ascii=False, indent=2))
    else:
        print("[kb_search] 需要 --query 或 --questions", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
