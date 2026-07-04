---
name: notebooklm-usage
description: COWORK 工作区使用 NotebookLM 的方法——禁止 pip install，用 nblm.py 调用
---

# NotebookLM 在 COWORK 工作区的使用

## 永久禁止：不要 pip install
代理 localhost:3128 会拦截 PyPI。notebooklm-py 已安装在系统 Python 中。

## 调用方式
```bash
python "C:\Users\周通\nblm.py" list
python "C:\Users\周通\nblm.py" ask --notebook-id <id> --question "问题"
```
