# CHANGELOG

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
