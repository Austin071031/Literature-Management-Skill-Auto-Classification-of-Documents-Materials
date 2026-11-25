---
name: research-library-curator
description: 科研文献与资料自动分类整理（可回滚整理＋可检索问答）。当任务给出混杂科研文件（论文 PDF/预印本/会议/学位论文/补充材料/数据集/扫描件）及随附管理记录（别名表/版本说明/元数据表），要求分类归档、补元数据、统一命名、识别重复与版本关系、建索引并带引用回答问题时使用。真实改动目录（复制非剪切，源目录只读）；元数据仅依据原文/侧车/管理记录，缺失如实标注不补造；别名与版本指令优先于启发式；全程审计日志＋一键回滚；索引按页切块，问答逐条附文件/页码证据，无依据如实回答。输出 /app/output/result.json（含 output_contract 全字段＋case_id）、library/、manifest、index/、answers.json。仅适用已有文件批次的整理与检索；不适用文献检索发现、精读翻译、写作润色。
---

# 科研文献与资料自动分类整理 Skill

## 用途与适用条件
把 `/input` 下的一批科研资料真实整理成可交接的资料库：按文献类型归入目录层级、
提取标题/作者/年份/期刊/DOI/arXiv 等元数据、按统一模板重命名、识别精确重复与
预印本↔正式版版本关系、生成可检索清单、全程审计日志且可一键回滚。

适用：输入为文件目录（PDF/文本/BibTeX/RIS/CSV/CIF 等），要求分类、命名、去重、批量整理。
不适用：文献检索发现（去网上找新文献）、单篇精读翻译润色；遇此应说明并退出。

## 红线（违反即失败）
1. **不补造元数据**：标题/作者/年份/DOI 只能来自原文文本层、PDF 元数据或同名侧车
   （.bib/.ris/.enw）；提取不到就写 null 并注明 `not_found`。绝不从文件名或常识猜测补全。
2. **不删除、不覆盖**：源目录（/input）只读；所有结果写入 /app/output；重复与旧版本
   移入 `_archive/` 而非删除；目标冲突时改唯一名而非覆盖。
3. **真实改动目录**：交付物必须是实际生成的目录与文件，不是聊天里的建议清单。
4. **契约完整**：`result.json` 必须含 `case_id` 与 case.json `output_contract` 的
   **全部字段**；无法满足的字段给 null 并写明原因，不得遗漏键。
5. **诚实状态**：部分完成必须 `status: "partial"` 并在 `exceptions` 中逐条列出
   跳过/失败/冲突，不把未完成写成完成。
6. **可复核**：每条分类与去重决策附规则编号与证据（manifest 的 reason / *_source 列）。

## 输入与输出
- 输入：`/input/case.json`（case_id、output_contract、约束、可选 questions/searches 字段）、
  `/input/task.md`（整理规则、可选问句）、`/input` 下的材料文件（可能含子目录），
  以及随附的**管理性材料**（别名表/版本说明/元数据表，如 aliases.txt、version_notes.md、metadata.csv）。
- 输出（`/app/output/`）：
  - `result.json` — case_id + output_contract 全字段 + status/sources/uncertainty/change_log/exceptions
  - `library/` — 整理后的资料库（默认 `library/<文献类型>/<年份>/`）
  - `_archive/duplicates/`、`_archive/versions/` — 重复件与被取代版本（保留不删）
  - `_archive/admin/` — 管理性材料原件（内容已解析应用，不入库）
  - `manifest.csv` / `manifest.json` — 每份输入文件：原路径、sha256、动作、新路径、
    元数据及字段来源（source/confidence）、标签、归属依据
  - `index/` — 可检索索引（chunks.jsonl 按页切块 + inverted.json 倒排 + stats.json）
  - `answers.json` — 案例检索/问答请求的答案（每条附 文件/页码/块号 证据；无依据如实标注）
  - `audit/operations.jsonl` — 全量操作审计日志（追加式，跨多次运行）
  - `audit/rollback.sh` — 一键回滚全部落盘操作
  - `README.md` — 人类可读摘要（目录树、统计、未解决项、冲突）
- 中间产物（`/app/work/`）：brief.json、admin.json、inventory.json/.csv、refs.json、
  plan.json、apply_report.json、questions.json、search_results.json、selfcheck.json、
  run_log.md — 全部保留供复核。

## 资源清单（安装后为 /skills/weekly-skill）
| 路径 | 作用 |
|-|-|
| `scripts/inspect_case.py` | 预检：读 case.json/task.md，提取 case_id、output_contract、约束提示与材料清单 → brief.json |
| `scripts/admin_notes.py` | 管理材料：解析别名表/版本说明/元数据表 → admin.json（无法解析的行留给 Agent 裁决） |
| `scripts/inventory.py` | 盘点：sha256/md5、魔数类型嗅探、权限、PDF 页数/加密/文本层检测 → inventory.json/.csv |
| `scripts/extract_refs.py` | 元数据：DOI/arXiv/标题/作者/年份/期刊/关键词提取（侧车优先，逐字段带 source/confidence）→ refs.json |
| `scripts/plan.py` | 计划：管理指令合并（元数据表补缺/别名分组/版本指令覆盖）、类型判定（T0–T11）、版本并查集分组、精确去重、受控标签、命名降级链 → plan.json |
| `scripts/apply.py` | 执行：复制落盘、幂等跳过、冲突改名不覆盖、追加审计日志、生成全历史回滚脚本 → apply_report.json |
| `scripts/kb_index.py` | 索引：library 内文件按页提取、切块、倒排索引（含文件/页码/块号坐标）→ index/ |
| `scripts/kb_search.py` | 检索：BM25 打分＋中英同义扩展＋短语奖励，单查询或批量 |
| `scripts/answer_questions.py` | 问答：从 case.json/task.md 提取检索/问答请求，带证据回答，无依据如实标注 → answers.json |
| `scripts/report.py` | 汇总：result.json（契约字段启发自动映射）、manifest、README → /app/output |
| `scripts/validate_output.py` | 机读自查：契约字段齐全、目标存在且哈希一致、审计完备 → selfcheck.json |
| `scripts/run_pipeline.sh` | 一键流水线（含失败保底 partial 交付） |
| `references/naming_rules.md` | 命名模板、降级链、特殊字符与超长标题处理 |
| `references/taxonomy_and_tags.md` | 文献类型判定规则表、受控标签词表与同义合并 |
| `references/output_schema.md` | /app/output 布局与 result.json 字段说明 |
| `references/edge_cases.md` | 损坏/加密/扫描件/乱码/权限/同名不同版本处置 |
| `references/worked_example.md` | 合成示例全流程演示（含每条规则命中示例） |

依赖：python3 ≥ 3.9（仅标准库）+ poppler-utils（pdftotext/pdfinfo，环境已预装）。
无网络依赖，不调用任何外部 API。

## 执行流程（严格按序；每步结果追加到 /app/work/run_log.md）

### 第 0 步：预检与规则识别
1. `python3 /skills/weekly-skill/scripts/inspect_case.py` 读 `brief.json`：
   确认 `case_id`、`output_contract` 字段列表、材料数量、issues。
2. **读 `/input/task.md` 全文**，识别题面是否指定：命名模板、目录维度（类型/主题/年份/项目）、
   是否 dry-run、是否指定输出目录名。若题面有明确规则，写 `/app/work/plan_config.json`
   覆盖默认值（字段见 `references/naming_rules.md` 第 3 节）：
   ```json
   {"library_root": "library", "directory_scheme": "by_type_year",
    "naming_template": "{first_author}-{year}-{title_slug}", "max_tags": 6}
   ```
   题面无明确指定时使用默认值。**题面规则优先于默认配置**。

### 第 1 步：运行流水线
```bash
bash /skills/weekly-skill/scripts/run_pipeline.sh /input /app/work /app/output /app/work/plan_config.json
```
（第 4 个参数可省略。）流水线依次执行 inspect→inventory→extract→plan→apply→report→validate，
任何一步失败自动走保底分支：仍生成 `result.json`（status=partial）并注明失败步骤。

### 第 2 步：抽验（必须做，这是"结果正确性"的证据）
流水线确定性完成分类/命名/去重，但 PDF 启发式提取的标题/作者是 low confidence。
用**不超过 3 次**读取抽验：
1. 从 `/app/work/refs.json` 取 2–3 篇 `title.confidence == "low"` 的条目，
   用 `pdftotext -f 1 -l 1 <pdf> - | head -30` 打开原文核对标题与第一作者；
   若提取错误，**直接编辑 `/app/work/refs.json` 修正该字段**（把 source 改为
   `"manual_verified"`、confidence 改为 `"high"`），然后重跑 plan/apply/kb_index/answers/report/validate：
   ```bash
   python3 /skills/weekly-skill/scripts/plan.py --work-dir /app/work \
     --config /app/work/plan_config.json 2>/dev/null || python3 /skills/weekly-skill/scripts/plan.py --work-dir /app/work
   python3 /skills/weekly-skill/scripts/apply.py --work-dir /app/work --output-dir /app/output
   python3 /skills/weekly-skill/scripts/kb_index.py --work-dir /app/work --output-dir /app/output
   python3 /skills/weekly-skill/scripts/answer_questions.py --work-dir /app/work --output-dir /app/output
   python3 /skills/weekly-skill/scripts/report.py --work-dir /app/work --output-dir /app/output
   python3 /skills/weekly-skill/scripts/validate_output.py --work-dir /app/work --output-dir /app/output
   ```
2. 核对 plan.json 的 `version_groups` 与 `admin_integration`：同组文件确实是同一工作的
   不同版本；管理指令（别名/版本说明/元数据表）应用无误；`unparsed_admin_lines` 非空时
   **人工阅读该管理文件**，将其指令以同样结构补写进 `/app/work/admin.json` 后重跑。
3. 若案例含检索/问答请求：打开 `/app/output/answers.json`，逐条审阅——
   `answered` 条目按 evidence 把 `answer_draft`（证据摘录）**改写为对问题的直接回答**
   （保留文件/页码引用）；`no_evidence` 条目确认确实无据后保持原样。禁止无证据编造答案。

### 第 3 步：补齐契约字段
打开 `/app/output/result.json`：
1. 检查 `output_contract` 各键：脚本已按键名启发自动映射（library/manifest/dedup/version/
   log/readme/tag 类），对照 task.md 确认映射正确；**未自动填充（delivered=null）的字段
   必须由你按 task.md 的真实要求填充**（指向 /app/output 下真实存在的文件或结构），
   无法满足的写明原因（如"案例未提供××材料"）。
2. 在 `uncertainty` 中补充你抽验后仍存在的不确定点（低置信标题、疑似扫描件等）。
3. 确认 `status` 与实际一致（有跳过/失败/冲突 → partial）。

### 第 4 步：机读自查与交付
1. `validate_output.py` 必须 `passed: true`；有 problems 逐条修复后重跑。
2. 自查清单（对照 selfcheck.json 与 manifest）：
   - [ ] 每份输入文件在 manifest 中恰好一行，action 明确（place/archive_duplicate/
     archive_version/skip），skip 均附原因
   - [ ] 每个 contract 字段有交付物或 null+原因
   - [ ] operations.jsonl 行数 ≥ 文件数 +2（run_start/run_end）
   - [ ] library/ 下文件真实存在且与 manifest target_path 一致
3. 最终答复中给出：整理统计（放置/归档/跳过/冲突数）、result.json 路径、
   回滚命令 `bash /app/output/audit/rollback.sh`，并如实说明 partial 项。

## 预算纪律（64 次请求 / 900 秒）
- 分类、命名、去重、归档、索引、检索全部由脚本确定性完成，**不要逐篇阅读 PDF 全文**；
  模型只用于：识别 task.md 规则（第 0 步）、抽验 2–3 条低置信元数据与未解析管理行（第 2 步）、
  审阅改写 answers.json 的答案草稿、填充契约字段（第 3 步）。
- 第 1 步完成后 result.json 已存在（保底交付），后续步骤是增量改进；
  时间紧张时优先保证第 0、1、4 步完成。
- 文件量巨大（>500）时脚本仍秒级完成；不要逐文件用模型处理。

## 异常处理速查（详见 references/edge_cases.md）
| 情况 | 处置 |
|-|-|
| 损坏 PDF（pdfinfo 报错） | action=skip，记入 exceptions.skipped 与 uncertainty |
| 加密 PDF | 同上，单独列入 encrypted_pdfs |
| 扫描件（无文本层） | 归入 scanned_document/，元数据缺失如实标注，禁止臆造 |
| 同名不同版本 | 冲突改名（加 sha 短后缀），记 conflicts，不覆盖 |
| 精确重复（同 sha256） | 保留文件名最干净的一份，其余归档 _archive/duplicates |
| 预印本+正式版 | 并查集分组，元数据更全者为 canonical，其余归档 _archive/versions |
| 权限不足 | inventory 记录 perm_mode 与 readable=false，跳过并记录 |
| 中文/多语言标题 | slug 保留 CJK 字符；见 naming_rules.md |

## 最小调用示例
见 `examples/minimal_example.md`（合成输入，输出标注为示例，非正式案例结果）。
