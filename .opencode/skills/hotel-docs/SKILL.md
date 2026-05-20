---
name: hotel-docs
description: 酒店管理文档自动生成——SOP标准操作流程、会议纪要、合同协议、培训手册、客诉记录。输入"酒店""SOP""会议纪要""合同""培训手册""客诉"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write
metadata:
  language: zh-CN
---

## 强制规则
**所有文字输出必须是中文。** 你说需求，出文档。

## 工作流程

### Step 1: 解析需求 → 匹配文档类型
读取用户输入，自动匹配文档类型：

```python
# 类型匹配逻辑
doc_types = {
    "SOP":         ["标准操作", "流程", "操作规范", "sop"],
    "会议纪要":     ["开会", "会议", "记录", "纪要"],
    "合同协议":     ["合同", "协议", "签约"],
    "培训手册":     ["培训", "新人", "入职", "带教"],
    "客诉记录":     ["投诉", "客诉", "纠纷", "差评"],
}

matched_type = None
for doc_type, keywords in doc_types.items():
    if any(kw in user_input for kw in keywords):
        matched_type = doc_type
        break
```

如果未匹配到任何类型，主动提问引导用户选择。

### Step 2: 按模板生成文档
根据文档类型使用对应模板：

**SOP 模板**
```md
# [酒店名称] - [流程名称] 标准操作流程
| 步骤 | 岗位 | 操作内容 | 工具/材料 | 质量标准 | 备注 |
|------|------|----------|-----------|----------|------|
| 1 | 前台 | [操作] | [工具] | [标准] | [备注] |
```

**会议纪要模板**
```md
# [酒店名称] - 会议纪�