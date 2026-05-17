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

### 创建异常
- `skills.sh` 不可达 → 改用 GitHub topics 搜索 `opencode-skill`
- 目录 `.opencode/skills/<name>/` 已存在 → 询问覆盖/合并/跳过
- description缺少触发词 → 自动补全并提示用户确认

### 查找异常
- 搜索结果为空 → 提示用户换关键词，或检查 skills.sh 状态
- 目标 skill 需要未安装的依赖 → 先安装依赖再加载 skill

### 安装异常
- `npx skills add` 失败 → 提示手动下载 SKILL.md 放入对应目录
- 版本冲突（已有同名 skill）→ 询问升级/保留当前/备份旧版

### 优化异常
- SKILL.md 不存在 → 提示先创建 skill
- 优化建议被用户否决 → 只应用部分建议，保留用户选择的原内容
