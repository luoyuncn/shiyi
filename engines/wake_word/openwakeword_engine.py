"""OpenWakeWord唤醒词引擎"""
import numpy as np
from openwakeword import Model
from engines.base import BaseEngine
from loguru import logger
from typing import Optional


class OpenWakeWordEngine(BaseEngine):
    """OpenWakeWord唤醒词检测引擎"""

    def __init__(self, model_path: Optional[str] = None, threshold: float = 0.5):
        """
        初始化唤醒词引擎

        Args:
            model_path: 自定义模型路径，None表示使用预训练模型
            threshold: 检测阈值 (0-1)，越高越严格
        """
        self.model_path = model_path
        self.threshold = threshold
        self.model = None

    async def initialize(self):
        """加载唤醒词模型"""
        try:
            # 如果没有自定义模型，使用预训练模型
            if self.model_path:
                self.model = Model(wakeword_models=[self.model_path])
                logger.info(f"唤醒词模型已加载: {self.model_path}")
            else:
                # 使用默认的hey_mycroft模型
                self.model = Model()
                logger.info("唤醒词模型已加载: 默认预训练模型")

            logger.debug(f"可用的唤醒词: {list(self.model.models.keys())}")

        except Exception as e:
            logger.error(f"加载唤醒词模型失败: {e}")
            raise

    async def detect(self, audio_chunk: np.ndarray) -> bool:
        """
        检测音频块中是否包含唤醒词

        Args:
            audio_chunk: 音频数据 (numpy数组, int16格式)

        Returns:
            是否检测到唤醒词
        """
        if self.model is None:
            raise RuntimeError("唤醒词模型未初始化")

        try:
            # 预测
            prediction = self.model.predict(audio_chunk)

            # 检查所有模型的预测结果
            for model_name, score in prediction.items():
                if score >= self.threshold:
                    logger.info(f"✨ 检测到唤醒词: {model_name} (置信度: {score:.2f})")
                    return True

            return False

        except Exception as e:
            logger.error(f"唤醒词检测失败: {e}")
            return False

    async def cleanup(self):
        """清理资源"""
        self.model = None
        logger.info("唤醒词引擎已清理")
