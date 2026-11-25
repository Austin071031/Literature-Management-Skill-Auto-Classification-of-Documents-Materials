#!/usr/bin/env python3
"""answer_questions.py — 提取案例中的检索/问答请求并带来源回答。

问题来源（按优先级）:
1. case.json 的 questions / searches / queries / tasks 字段（list[str] 或 list[dict]）;
2. task.md 中的问句行（以 ？/? 结尾）与编号列表行。

回答纪律:
- 有证据：答案 = 证据摘录 + 引用（文件/页码/块号），confidence=high|medium；
- 证据不足（最高分低于阈值）：明确回答"未在资料库中找到依据"并说明缺口，不编造。

用法: python3 answer_questions.py [--work-dir /app/work] [--output-dir /app/output]
输出: /app/work/questions.json, /app/output/answers.json
"""
import argparse, json, os, re, subprocess, sys

def extract_questions(case, task_text):
    qs = []
    for key in ("questions", "searches", "queries", "tasks"):
        v = case.get(key)
        if isinstance(v, list):
            for i, item in enumerate(v, 1):
                if isinstance(item, str):
                    qs.append({"id": f"{key}-{i}", "question": item, "origin": f"case.json:{key}"})
                elif isinstance(item, dict):
                    q = item.get("question") or item.get("query") or item.get("task") or item.get("q")
                    if q:
                        qs.append({"id": item.get("id") or f"{key}-{i}",
                                   "question": str(q), "origin": f"case.json:{key}"})
        elif isinstance(v, str) and v.strip():
            qs.append({"id": key, "question": v.strip(), "origin": f"case.json:{key}"})
    if qs:
        return qs
    # task.md 问句与编号行
    for i, line in enumerate(task_text.splitlines(), 1):
        s = line.strip()
        if not s or len(s) < 6:
            continue
        if s.endswith(("？", "?")) or re.match(r"^\d+[\.\)、]\s*\S+", s) and any(
                k in s for k in ("哪", "什么", "列出", "找出", "检索", "搜索", "查询", "是否", "有没有")):
            qs.append({"id": f"task-{i}", "question": s, "origin": f"task.md:L{i}"})
    return qs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--min-score", type=float, default=2.0)
    args = ap.parse_args()

    brief_path = os.path.join(args.work_dir, "brief.json")
    if not os.path.exists(brief_path):
        print("[answer_questions] 缺少 brief.json", file=sys.stderr)
        return 2
    with open(brief_path, "r", encoding="utf-8") as f:
        brief = json.load(f)

    case = {}
    case_path = os.path.join(brief.get("input_dir", "/input"), "case.json")
    if os.path.exists(case_path):
        with open(case_path, "r", encoding="utf-8") as f:
            case = json.load(f)
    task_text = ""
    if os.path.exists(brief.get("task_path", "")):
        with open(brief["task_path"], "r", encoding="utf-8") as f:
            task_text = f.read()

    questions = extract_questions(case, task_text)
    with open(os.path.join(args.work_dir, "questions.json"), "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    if not questions:
        print("[answer_questions] 未在 case.json/task.md 发现检索或问答请求")
        with open(os.path.join(args.output_dir, "answers.json"), "w", encoding="utf-8") as f:
            json.dump({"questions_total": 0, "answers": [],
                       "note": "案例未提出检索/问答请求"}, f, ensure_ascii=False, indent=2)
        return 0

    if not os.path.exists(os.path.join(args.output_dir, "index", "inverted.json")):
        print("[answer_questions] 缺少索引，请先运行 kb_index.py", file=sys.stderr)
        return 2
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import kb_search
    inverted, doc_len, chunks = kb_search.load_index(args.output_dir)

    answers = []
    for q in questions:
        hits = kb_search.search(q["question"], inverted, doc_len, chunks, args.topk)
        if hits and hits[0]["score"] >= args.min_score:
            best = hits[0]
            answers.append({
                "id": q["id"], "question": q["question"], "origin": q["origin"],
                "status": "answered",
                "confidence": "high" if best["score"] >= args.min_score * 2.5 else "medium",
                "answer_draft": best["excerpt"],
                "evidence": [{"file": h["file"], "page": h["page"],
                              "chunk_id": h["chunk_id"], "score": h["score"],
                              "excerpt": h["excerpt"][:160]} for h in hits[:3]],
                "note": "草稿为最高分证据摘录；Agent 应阅读 evidence 后改写为直接回答",
            })
        else:
            answers.append({
                "id": q["id"], "question": q["question"], "origin": q["origin"],
                "status": "no_evidence",
                "confidence": "high",
                "answer_draft": "资料库中未找到足以回答该问题的依据。",
                "evidence": [],
                "note": "最高检索得分低于阈值，如实回答无依据而非编造",
            })

    out = {"questions_total": len(questions),
           "answered": sum(1 for a in answers if a["status"] == "answered"),
           "no_evidence": sum(1 for a in answers if a["status"] == "no_evidence"),
           "answers": answers}
    with open(os.path.join(args.output_dir, "answers.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[answer_questions] total={out['questions_total']} answered={out['answered']} "
          f"no_evidence={out['no_evidence']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
