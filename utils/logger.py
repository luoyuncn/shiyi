"""日志配置模块"""
from loguru import logger
import sys
from pathlib import Path


def setup_logger(log_level: str = "INFO", suppress_stdout: bool = False):
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        suppress_stdout: 为 True 时不输出到 stdout（TUI 模式使用）
    """
    # 移除默认处理器
    logger.remove()

    # 控制台输出 - 带颜色和emoji（TUI 模式下跳过）
    if not suppress_stdout:
        logger.add(
            sys.stdout,
            level=log_level,
            format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <level>{message}</level>",
            colorize=True
        )

    # 确保logs目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # 文件输出 - 详细日志
    logger.add(
        "logs/assistant_{time:YYYY-MM-DD}.log",
        rotation="00:00",  # 每天午夜轮转
        retention="7 days",  # 保留7天
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:8} | {name}:{function}:{line} - {message}",
        encoding="utf-8"
    )

    if not suppress_stdout:
        logger.info("📋 日志系统已初始化")
