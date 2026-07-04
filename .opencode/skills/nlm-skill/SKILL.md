---
name: nlm-skill
description: 连接 Google NotebookLM 进行深度研究——列出笔记本、提问、上传文档、生成音频概览、幻灯片、思维导图等。已安装在系统 Python，无需 pip install。
allowed-tools: Read Bash Write Glob Grep
---

# NotebookLM 技能（COWORK 区域）

将 Google NotebookLM 的研究能力接入 COWORK（OpenCode AI Desktop）。

## 重要：无需 pip install

**notebooklm-py 已安装在系统 Python 中**，不需要也不能通过 pip 安装（COWORK 环境的 3128 代理会阻止 PyPI 连接）。

所有命令统一通过通用包装器调用：
```bash
python "C:\Users\周通\nblm.py" <命令>
```

`nblm.py` 自动设置 7890 代理并调用系统 Python 的 notebooklm 模块，不受 COWORK 环境代理限制。

备用（如果上面不行，用完整路径）：
```bash
"C:\Users\周通\AppData\Local\Programs\Python\Python312\python.exe" -m notebooklm <命令>
```

## 前置条件（已完成）

- ✅ `notebooklm-py` v0.4.1 已安装在系统 Python
- ✅ Google 认证已保存（跨所有区域共享）
- ✅ 代理 `127.0.0.1:7890` 运行中（包装器自动设置）
- ❌ 不需要也不尝试 pip install

## 常用命令

### 笔记本管理
```bash
python "C:\Users\周通\nblm.py" list
python "C:\Users\周通\nblm.py" create --title "笔记本名称"
python "C:\Users\周通\nblm.py" delete --id <id>
```

### 资料管理
```bash
python "C:\Users\周通\nblm.py" source list --notebook-id <id>
python "C:\Users\周通\nblm.py" source add --notebook-id <id> --url "https://..."
python "C:\Users\周通\nblm.py" source add --notebook-id <id> --file path.pdf
```

### 提问与分析
```bash
python "C:\Users\周通\nblm.py" ask --notebook-id <id> --question "你的问题"
python "C:\Users\周通\nblm.py" summary --notebook-id <id>
python "C:\Users\周通\nblm.py" chat history --notebook-id <id>
```

### 内容生成
```bash
python "C:\Users\周通\nblm.py" generate audio --notebook-id <id>
python "C:\Users\周通\nblm.py" generate slide-deck --notebook-id <id>
python "C:\Users\周通\nblm.py" generate mind-map --notebook-id <id>
python "C:\Users\周通\nblm.py" generate flashcards --notebook-id <id>
python "C:\Users\周通\nblm.py" generate quiz --notebook-id <id>
python "C:\Users\周通\nblm.py" generate report --notebook-id <id>
python "C:\Users\周通\nblm.py" generate infographic --notebook-id <id>
```

### 使用默认笔记本（免输 ID）
```bash
# 设置默认
python "C:\Users\周通\nblm.py" use <id前缀>

# 之后直接提问
python "C:\Users\周通\nblm.py" ask --question "问题"
```

## 关键词
notebooklm, nlm, notebook, google notebooklm, AI 研究, 文档分析, 知识管理, 播客生成, 幻灯片, 思维导图
