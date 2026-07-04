---
name: web-scraper
description: >-
  网页数据采集——基于 Firecrawl 引擎，支持单页抓取、批量爬取、结构化提取、搜索采集。
  适配酒店OTA价格监控、竞品分析、影视热点追踪。输出JSON/Excel到 outputs/ 目录。
  输入"抓取""爬虫""数据采集""网页数据""竞品""爬一下""采集数据"时触发。
  所有文字输出为中文。
license: MIT
compatibility: opencode
allowed-tools: Bash(python:*) Read Write WebFetch
metadata:
  language: zh-CN
  audience: hotel-professional
---

## 强制规则
所有文字输出必须是中文。采集的数据以中文标注字段名。输出到 `outputs/` 目录（JSON 或 Excel）。

## 测试用例
本技能配套测试数据见 `test-prompts.json`，包含 3 个典型场景。测试用例索引：

| ID | Prompt | 覆盖功能 | 预期产出 |
|----|--------|---------|---------|
| 1 | 爬携程上海五星酒店价格前10家 | 批量采集 + JSON/Excel输出 | 含酒店名称/房型/价格/评分的结构化数据 |
| 2 | 监控竞品酒店价格每日更新 | 定时采集 + Excel输出 | 含多日价格趋势的竞品对比表 |
| 3 | 搜索热点电影的话题热度 | 搜索采集 + JSON输出 | 含标题/热度/来源/日期的榜单数据 |

## 做什么
从网页抓取结构化数据，用于酒店竞品价格监控、市场情报收集、影视热点话题追踪。Firecrawl 内建 AI 提取能力，可自动将网页转为结构化 JSON。

## 检查点总览（每次操作前必确认）

| # | 操作 | 检查点 | 确认内容 |
|---|------|--------|---------|
| 1 | 单页抓取 | 抓取前确认 | URL 是否正确？是否遵守 robots.txt？ |
| 2 | 批量爬取 | 爬取前确认 | limit 是否 ≤20（避免被封）？是否已配置爬取间隔？ |
| 3 | 搜索采集 | 搜索前确认 | 关键词是否准确？limit 是否在免费额度内（500次/月）？ |
| 4 | 结构化提取 | 提取前确认 | 字段定义是否覆盖所需数据？输出格式 JSON 还是 Excel？ |
| 5 | Excel 输出 | 导出前确认 | 表头是中文？是否需要配合 hotel-bi 生成图表？ |

## 采集模式

| 模式 | 说明 | 输出 | 适用场景 |
|------|------|------|----------|
| **单页抓取** | 指定URL → 提取内容 | Markdown/JSON | 单页面数据 |
| **批量爬取** | 起始URL → 递归爬取同站 | JSON列表 | 酒店列表/影视合集 |
| **搜索采集** | 关键词 → 搜索引擎结果 | JSON列表 | 热点追踪 |
| **结构化提取** | URL + 提取规则 → 字段 | Excel | 价格/评分/标题 |

## 工作流

### 1. 单页数据抓取
> **检查点①：** 确认目标 URL 格式正确、爬取权限已检查后再执行。

```python
from firecrawl import Firecrawl

app = Firecrawl(api_key="your-key")  # 也可无key使用免费额度

# 抓取网页为 Markdown
result = app.scrape("https://hotel.ctrip.com/hotel/12345.html")
print(result["markdown"])

# 保存数据
import json
with open("outputs/hotel_data.json", "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
```

### 2. 酒店竞品数据采集模板
> **检查点②：** 确认 limit 不超过 20、爬取间隔 >60 分钟后再运行。

```python
# OTA酒店搜索页爬取
result = app.crawl(
    "https://hotel.ctrip.com/hotel/shanghai",
    params={
        "limit": 20,
        "scrapeOptions": {
            "formats": ["markdown"],
        }
    }
)

# 搜索结果采集
result = app.search(
    "上海五星级酒店 价格 2025",
    params={"limit": 10}
)
```

### 3. 数据输出格式

**JSON 输出** (`outputs/hotel_prices.json`)：
```json
[
  {
    "酒店名称": "上海和平饭店",
    "房型": "豪华大床房",
    "今日价格": 1880,
    "评分": 4.7,
    "采集时间": "2025-05-16"
  }
]
```

**Excel 输出** (`outputs/xlsx/竞品价格监控.xlsx`)：
> **检查点⑤：** 确认表头为中文字段名、数据列与 hotel-bi 输入格式兼容。

自动写入格式化 Excel，含价格对比图表（配合 hotel-bi 技能）。

### 4. 影视热点追踪
> **检查点③：** 确认关键词覆盖目标话题、limit 在免费额度内。

```python
# 搜索影视热点
result = app.search("大明王朝1566 解说 热点", params={"limit": 20})
# 提取标题、热度、发布日期
```

### 5. 与 hotel-bi 集成
```
web-scraper → outputs/hotel_prices.json → hotel-bi (skill) → 经营分析报表 (outputs/xlsx/)
web-scraper → outputs/competitor_data.json → hotel-docs (skill) → 竞品分析报告 (outputs/docx/)
web-scraper → outputs/market_trends.json → ralph-cycle (skill) → 自动化周报流水线
```

## 异常处理与降级策略

| 场景 | 表现 | 处理方式 |
|------|------|---------|
| Firecrawl API 不可用 | 请求超时 / 401 | 降级到 `requests + BeautifulSoup` 原生方案 |
| API Key 配额耗尽 (500次/月) | 返回 429 | 提示用户配置 API Key，使用本地缓存度过配额周期 |
| 目标网站反爬拦截 | 返回 403 / 验证码页面 | 增加 User-Agent 伪装 + 随机延迟 (2-5s)，仍失败则报"目标站需人工处理" |
| 批量爬取死循环 | 同 URL 反复出现 | 内置 URL 去重集合，同页不重复爬取 |
| JSON 解析失败 | 返回非 JSON 格式 | 转为 Markdown 原始输出，附加结构解析建议 |
| 搜索结果为空 | 返回空列表 | 建议更换关键词 / 检查网络 / 确认搜索引擎是否可用 |
| Excel 写入失败 | openpyxl 报错 | 降级到 CSV 输出 (`outputs/<name>.csv`) |
| 数据编码乱码 | 中文显示为 `\uXXXX` | 强制 `encoding="utf-8"` 写入，确保 `ensure_ascii=False` |

### Firecrawl API 不可用时原生降级方案
```python
import urllib.request
from bs4 import BeautifulSoup  # pip install beautifulsoup4

html = urllib.request.urlopen("https://example.com").read()
soup = BeautifulSoup(html, "html.parser")
```

## 注意事项
1. 遵守目标网站的 robots.txt 和爬取频率限制
2. Firecrawl 免费额度：500次/月，超量需 API Key
3. 采集酒店数据仅用于个人竞品分析，禁止商业转售
4. 数据自动缓存到 `outputs/` 目录，避免重复抓取
