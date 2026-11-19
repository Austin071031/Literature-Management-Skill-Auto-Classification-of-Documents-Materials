# 最小调用示例（示例标注：非正式案例结果）

## 输入

```
/input/
├── case.json          # {"case_id": "demo", "output_contract": {"organized_library": "...", "metadata_manifest": "..."}}
├── task.md            # "整理文献：分类归档、统一命名、识别重复与版本关系"
├── paper_a.pdf        # 含 DOI 的期刊论文（合成）
└── paper_a_copy.pdf   # paper_a.pdf 的逐字节副本（合成）
```

## 调用

```bash
bash /skills/weekly-skill/scripts/run_pipeline.sh /input /app/work /app/output
python3 /skills/weekly-skill/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
```

## 示意输出（示例，非正式案例结果）

```
/app/output/
├── result.json            # case_id=demo, status=success, output_contract 两字段均已交付
├── manifest.csv           # 2 行：paper_a.pdf → place；paper_a_copy.pdf → archive_duplicate
├── README.md
├── library/journal_article/2023/Author-2023-Some_Title.pdf
└── audit/{operations.jsonl, rollback.sh}
```

result.json 关键片段（示例）：

```json
{
  "case_id": "demo",
  "status": "success",
  "statistics": {"placed": 1, "archived": 1, "already_applied": 0,
                 "conflict_renamed": 0, "skipped": 0, "failed": 0},
  "elements": {"duplicates": [{"kept": "paper_a.pdf", "archived": ["paper_a_copy.pdf"]}]},
  "output_contract": {
    "organized_library": {"delivered": "library"},
    "metadata_manifest": {"delivered": "manifest.csv"}
  }
}
```

## 说明

- 以上文件名、DOI、统计数字均为合成演示数据；
- 正式运行时以 /input 真实材料为准，脚本不内置任何案例答案；
- 完整合成示例（10 份异构输入，覆盖全部规则 T0–T11）见
  `references/worked_example.md`。
