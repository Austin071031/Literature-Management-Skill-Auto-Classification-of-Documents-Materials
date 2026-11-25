# CHANGELOG

## 1.1.0 (2026-11-25)

针对隐藏案例工单中的"别名、管理性版本说明、元数据、检索/问答、恢复/索引操作"新增：

- **管理性材料整合**（admin_notes.py + plan.py 合并逻辑）：解析别名表
  （canonical = alias 或 alias -> canonical）、版本说明（superseded by / replaces /
  authoritative）与元数据表（CSV/JSON）；元数据表仅补缺失字段（source=admin_metadata），
  别名并入版本分组键，版本指令覆盖启发式 canonical 选择；无法解析的行保留供 Agent 裁决。
  管理文件原件归档 `_archive/admin/` 不入库。
- **可检索索引**（kb_index.py）：library 内文件逐页提取、切块（600 字窗口/段落边界）、
  纯标准库倒排索引，块级坐标（文件/页码/块号）支持回链复核。
- **带引用的问答**（kb_search.py + answer_questions.py）：BM25 打分、中英领域同义
  双向扩展（解决中文提问对英文文献的词表鸿沟）、短语奖励；问题来自 case.json 的
  questions/searches/queries 字段或 task.md 问句；得分低于阈值如实回答"未找到依据"，
  禁止编造；答案草稿由 Agent 审阅改写为直接回答。
- result.json 新增 `knowledge_base` 与 `admin_integration` 段；契约字段自动映射
  扩展 answer/question/search/index/recovery 类键名。
- frontmatter description 压缩至 913B（≤1024B 上限，规避安装期 evaluation_error）。

## 1.0.0 (2026-11-19)

- 首版：六脚本流水线（inspect → inventory → extract_refs → plan → apply → report）
  + 机读自查（validate_output）+ 一键流水线（run_pipeline.sh，含失败保底）。
- 元数据：DOI/arXiv/年份正则 + 标题/作者保守启发 + BibTeX/RIS 侧车解析，
  逐字段 source/confidence/evidence；arXiv 号派生年份标注 arxiv_id_derived。
- 分类：T0–T11 规则表（dataset/supplement/scanned/thesis/preprint/conference/journal/other）。
- 版本：DOI 与（规范化标题+第一作者）双键并查集分组；canonical 打分保留，
  其余归档 _archive/versions。
- 去重：sha256 精确重复，保留文件名最干净者，归档 _archive/duplicates。
- 命名：模板降级链（unknown_author/ndate/untitled/原名+sha 短哈希），
  特殊字符与超长标题处理，命名空间按目标目录隔离，冲突不覆盖。
- 可靠性：幂等 already_applied、断点续跑、追加式审计日志、全历史回滚脚本、
  损坏/加密/扫描件/权限不足逐类处置并如实记录。
- 交付：result.json 含 output_contract 全字段（键名启发自动映射 + Agent 填充位）、
  六类要素交代、exceptions、uncertainty；manifest.csv/.json；README 摘要。
