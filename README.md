# kbqa-cited-research-knowledge-base

科研知识库问答与资料治理 Skill:对本地科研资料库完成盘点(哈希/权限/类型)、文本抽取(含扫描件 OCR 回退)、去重与版本链(支持管理方规则)、段落级锚点索引、带来源引用的检索问答、不确定性分级,并按案例 `output_contract` 合成可复核的 `result.json`。

## 安装与依赖

- 无第三方依赖:全部脚本仅使用 Python 3.8+ 标准库。
- PDF 文本抽取调用系统 `pdftotext`(随 poppler 提供);不可用时 PDF 自动标记 `needs_ocr`,由运行环境 OCR 工具回退。
- 安装方式:将整个目录置于 `/skills/weekly-skill/`(评测环境)或任意路径后,按 `SKILL.md` 的阶段 0–9 调用。

## 目录约定

- 输入:`/input/case.json`(case_id、资料库路径、output_contract)+ 资料库文件。
- 中间产物:`/app/work/`(inventory.json、extract_report.json、versions.json、index.jsonl、answers.json、ops_log.jsonl)。
- 交付:`/app/output/result.json`(合同字段完整)+ `report.md` + 复核材料(inventory/versions/extract/ops_log 副本)。

## 快速开始

见 `SKILL.md` 与各阶段命令;合成数据示例见 `examples/minimal-example.md`。

## 维护信息

- 脚本入口与职责:`scripts/kb_*.py`,每个脚本 `--help` 可查参数;全部幂等,可重复运行。
- 版本关系启发式(v/rev/draft/final/日期模式)可被 `--rules version_rules.json` 覆盖,管理方规定优先。
- 已知限制:不做语义向量检索(关键词检索 + 模型过目命中);legacy 二进制 Office(.doc/.xls)标记 unsupported;图片仅经 OCR 回退。
