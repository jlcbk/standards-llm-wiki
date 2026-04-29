# Extraction Rules

## PDF 到知识页流程

```text
PDF → 文本/OCR → 原文 Markdown → 标准主页面 → 条款页/主题页/索引页
```

## 抽取要求

1. 优先保留标准号、名称、发布日期、实施日期、替代关系、适用范围。
2. 条款号必须保持原样，不要改写成自然语言编号。
3. 表格应尽量转为 Markdown table；无法可靠转写时标记 `quality: low`。
4. 对强制性要求，区分：适用对象、约束动作、判定条件、例外情况。
5. 不确定信息不要补全，写 `unknown` 或放入 `_meta/unresolved-issues.md`。
6. 每个跨标准主题都应回链到具体标准与条款。

## 推荐工具

- 文字型 PDF：`pdftotext`、`docling`、`marker`
- 扫描型 PDF：OCR，例如 PaddleOCR、docling OCR
- 表格较多的 PDF：优先 `docling` 或 `marker`
