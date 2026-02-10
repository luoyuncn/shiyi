"""引擎基类 - 定义所有引擎的统一接口"""
from abc import ABC, abstractmethod


class BaseEngine(ABC):
    """所有引擎的抽象基类"""

    @abstractmethod
    async def initialize(self):
        """
        异步初始化引擎

        用于加载模型、建立连接等耗时操作
        """
        pass

    @abstractmethod
    async def cleanup(self):
        """
        清理资源

        释放模型、关闭连接等
        """
        pass
