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
Ralph循环：自动化软件开发的完整循环。

## 流程
1. **需求** → 拆解为可执行任务列表，展示给用户确认
2. **开发** → 逐任务编码（Read+Edit+Write），每步验证
3. **测试** → 运行 pytest/npm test 验证，失败则修复
4. **修复** → 读错误输出定位修复，回到步骤3
5. **提交** → git add+commit，展示diff给用户确认
6. **循环** → 下一任务直到全部完成

## 异常处理
- 测试失败≥3次：询问继续/跳过/终止
- 用户拒绝检查点：记录原因，跳下一任务
- Git冲突：提示路径，等手动解决

## 适用场景
- 多页面网站开发 / 批量功能实现 / 自动化测试修复
