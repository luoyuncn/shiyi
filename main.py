"""程序主入口"""
import asyncio
import os
from pathlib import Path
from loguru import logger
from config.settings import load_config
from utils.logger import setup_logger
from core.assistant import AssistantCore


async def main():
    """程序主函数"""
    # 检查.env文件
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ 错误: 未找到.env文件")
        print("请复制.env.example为.env并填入你的API密钥")
        print("命令: cp .env.example .env")
        return

    try:
        # 加载配置
        config = load_config()

        # 设置日志
        setup_logger(config.system.log_level)

        # 初始化助理
        assistant = AssistantCore(config)

        # 启动助理
        await assistant.start()

    except KeyboardInterrupt:
        logger.info("\n👋 接收到退出信号 (Ctrl+C)")

    except Exception as e:
        logger.exception(f"💥 程序异常退出: {e}")

    finally:
        if 'assistant' in locals():
            await assistant.cleanup()

        logger.info("=" * 60)
        logger.info("🏠 小跟班已关闭，再见！")
        logger.info("=" * 60)


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
