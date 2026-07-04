---
name: notebooklm
description: NotebookLM深度研究。禁止pip install（代理拦截PyPI）。notebooklm-py已装系统Python，用 python "C:\Users\周通\nblm.py" 调用
allowed-tools: Read Bash Write Glob Grep
---

# NotebookLM（COWORK工作区）

## 🚨 禁止 pip install
COWORK 环境代理 localhost:3128 会阻止 PyPI。notebooklm-py 已安装在系统 Python。

## 唯一调用方式
```bash
python "C:\Users\周通\nblm.py" list
python "C:\Users\周通\nblm.py" ask --notebook-id <id> --question "问题"
python "C:\Users\周通\nblm.py" source list --notebook-id <id>
python "C:\Users\周通\nblm.py" summary --notebook-id <id>
```

## 笔记本列表
- 酒店专家模型
- 经济学知识库
- 个人成长
- 星级酒店参考的餐饮SOP
- 餐饮服务标准与各班次作业流程
- 酒店学习

## 如果提示找不到命令
直接运行 `python "C:\Users\周通\nblm.py" --version` 验证。不要 pip install。
