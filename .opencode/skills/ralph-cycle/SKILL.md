---
name: ralph-cycle
description: Ralph开发循环——AI代理自动化开发。从需求到代码到测试到部署的完整自动化循环。输入"ralph""自动开发""开发循环"时触发。
license: MIT
compatibility: opencode
allowed-tools: Bash Read Write Glob Edit
metadata:
  language: zh-CN
---

## 做什么
Ralph循环：AI代理自动化软件开发的完整循环。从需求拆解到代码实现到测试验证到版本提交，全程自动流转。

## 适用场景
- 多页面网站开发 / 批量功能实现 / 自动化测试修复 / API端点开发

## 工作流程

### Step 1: 需求拆解
将用户需求拆解为可执行的任务清单，按依赖排序：

```
需求: "用户登录功能"
├── 任务1: 创建用户模型(User)和数据库表
├── 任务2: 实现注册API (/api/register) ← 依赖任务1
├── 任务3: 实现登录API (/api/login)   ← 依赖任务1
├── 任务4: 添加JWT认证中间件          ← 依赖任务2,3
└── 任务5: 编写登录页�