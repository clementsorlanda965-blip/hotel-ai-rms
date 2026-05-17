---
name: skill-manager
description: 技能管理——创建新技能、搜索已有技能、安装技能、评估优化技能。访问skills.sh生态。输入"创建技能""搜索技能""安装技能""找技能"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Glob WebFetch
metadata:
  language: zh-CN
---
## 做什么
管理opencode技能的全生命周期：创建、查找、安装、优化。

## 创建技能
1. 理解用户要什么能力
2. 按opencode规范生成SKILL.md：name(小写英文-连接)、description(含触发关键词)、metadata
3. 写入 `.opencode/skills/<name>/SKILL.md`

## 查找技能
1. 搜索GitHub topics: `opencode-skill`
2. 访问 https://skills.sh 浏览技能目录
3. 按stars/更新日期/兼容性排序推荐

## 安装技能
```bash
npx skills add <owner/repo@skill> -g -y
```
或手动下载SKILL.md放入对应目录。

## 优化技能
1. 读取现有SKILL.md
2. 检查是否符合opencode规范（name格式、description是否含触发词、目录名是否匹配）
3. 提出改进建议并应用

## 异常处理
- skills.sh不可达→改搜GitHub topics `opencode-skill`
- 目录已存在→询问覆盖/合并/跳过
- description缺触发词→补全后用户确认
- npx失败→手动下载SKILL.md放入对应目录
- 搜索无结果→换关键词重试
- SKILL.md不存在→提示先创建
- 用户否决建议→只应用用户同意的部分
