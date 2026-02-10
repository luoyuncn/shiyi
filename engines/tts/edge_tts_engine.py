"""Edge-TTS语音合成引擎"""
import edge_tts
from engines.base import BaseEngine
from loguru import logger
from typing import AsyncGenerator


class EdgeTTSEngine(BaseEngine):
    """Edge-TTS引擎 - 免费的微软语音合成"""

    def __init__(
        self,
        voice: str = "zh-CN-YunxiNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz"
    ):
        """
        初始化TTS引擎

        Args:
            voice: 语音名称 (如: zh-CN-YunxiNeural云希, zh-CN-XiaoxiaoNeural晓晓)
            rate: 语速调整 (如: +20%表示加快20%)
            pitch: 音调调整 (如: +5Hz表示提高音调)
        """
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def initialize(self):
        """初始化TTS引擎"""
        logger.info(f"Edge-TTS引擎已初始化: {self.voice} (语速:{self.rate}, 音调:{self.pitch})")

    async def synthesize_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        流式合成语音

        Args:
            text: 要合成的文本

        Yields:
            音频数据块
        """
        if not text or not text.strip():
            logger.warning("TTS收到空文本，跳过合成")
            return

        try:
            logger.debug(f"TTS合成文本: {text[:30]}{'...' if len(text) > 30 else ''}")

            # 创建通信对象
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )

            # 流式获取音频数据
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]

            logger.debug(f"✅ TTS合成完成: {text[:20]}...")

        except Exception as e:
            logger.error(f"TTS合成失败: {e}")
            raise

    async def synthesize(self, text: str) -> bytes:
        """
        一次性合成语音（非流式）

        Args:
            text: 要合成的文本

        Returns:
            完整的音频数据
        """
        chunks = []
        async for chunk in self.synthesize_stream(text):
            chunks.append(chunk)

        return b''.join(chunks)

    async def cleanup(self):
        """清理资源"""
        logger.info("TTS引擎已清理")
