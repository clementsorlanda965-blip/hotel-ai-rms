"""
logging_config.py —— Hotel AI-RMS 统一日志配置 v1.0

替代散落在 14 个模块中的 print() 调用，统一使用 Python logging。

特性：
  - 控制台 + 文件双输出
  - 按日期轮转（每天一个日志文件）
  - 模块级 logger 获取（`get_logger(__name__)`）
  - 告警级别以上自动触发飞书通知（可选）

日志级别使用规则：
  DEBUG   — 开发调试（采集中间步骤、SQL 查询）
  INFO    — 业务流程（采集完成、价格更新、报告生成）
  WARNING — 需关注但不影响功能（校验未通过但仍继续、竞对数据缺失）
  ERROR   — 功能异常（采集失败、数据库写入失败）
  CRITICAL — 系统级告警（数据库损坏、磁盘满、连续 3 次采集失败）

用法：
  from logging_config import get_logger
  logger = get_logger(__name__)
  logger.info("OTA价格采集完成: %d 条", count)

日志文件位置：
  所有日志 → E:\工作AI\酒店管理\数据分析\logs\
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# 日志目录
# ═══════════════════════════════════════════════════════════════

LOG_DIR = Path(r"E:\工作AI\酒店管理\数据分析\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / f"hotel_rms_{datetime.now().strftime('%Y%m%d')}.log"

# ═══════════════════════════════════════════════════════════════
# 格式化器
# ═══════════════════════════════════════════════════════════════

CONSOLE_FORMAT = logging.Formatter(
    "%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
    datefmt="%H:%M:%S",
)

FILE_FORMAT = logging.Formatter(
    "%(asctime)s  %(levelname)-8s  %(name)-20s  "
    "[%(filename)s:%(lineno)d]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# ═══════════════════════════════════════════════════════════════
# 根 Logger 配置（只配置一次）
# ═══════════════════════════════════════════════════════════════

_configured = False


def setup_logging(level: int = logging.INFO, console: bool = True,
                  file: bool = True) -> logging.Logger:
    """初始化全局日志配置。

    Args:
        level: 日志级别（默认 INFO）
        console: 是否输出到控制台
        file: 是否写入文件

    Returns: 根 logger
    """
    global _configured
    if _configured:
        return logging.getLogger("hotel_rms")

    root = logging.getLogger("hotel_rms")
    root.setLevel(level)
    root.handlers.clear()

    # 控制台
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(CONSOLE_FORMAT)
        root.addHandler(console_handler)

    # 文件（按日期轮转，保留 30 天）
    if file:
        file_handler = logging.handlers.TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # 文件记录 DEBUG+
        file_handler.setFormatter(FILE_FORMAT)
        root.addHandler(file_handler)

    # 第三方库降噪
    for noisy in ["urllib3", "selenium", "PIL", "matplotlib"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """获取模块级 logger。

    用法：
      from logging_config import get_logger
      logger = get_logger(__name__)
      logger.info("处理完成")
    """
    if not _configured:
        setup_logging()

    # 统一前缀 hotel_rms.
    if not name.startswith("hotel_rms"):
        name = f"hotel_rms.{name}"
    return logging.getLogger(name)


# ═══════════════════════════════════════════════════════════════
# 日志辅助
# ═══════════════════════════════════════════════════════════════

def log_function_call(logger: logging.Logger = None):
    """装饰器：自动记录函数调用和耗时。"""
    import time
    from functools import wraps

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            lg = logger or get_logger(func.__module__)
            lg.debug("→ %s()", func.__name__)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                lg.debug("← %s() — %.3fs", func.__name__, elapsed)
                return result
            except Exception as e:
                elapsed = time.perf_counter() - start
                lg.error("✗ %s() — %.3fs — %s: %s",
                         func.__name__, elapsed, type(e).__name__, e)
                raise
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════
# CLI 自测
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    setup_logging(level=logging.DEBUG)

    logger = get_logger("test")
    logger.debug("这是一条调试信息")
    logger.info("OTA价格采集完成: %d 条记录，覆盖 %d 家酒店", 4, 4)
    logger.warning("竞对价格数据缺失: %s", "德尔塔酒店")
    logger.error("数据库写入失败: %s", "connection timeout")

    print(f"\n日志文件: {LOG_FILE}")
    print(f"日志目录: {LOG_DIR}")
