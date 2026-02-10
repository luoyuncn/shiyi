"""腾讯云一句话识别引擎"""
import base64
import wave
from io import BytesIO
from tencentcloud.common import credential
from tencentcloud.asr.v20190614 import asr_client, models
from engines.base import BaseEngine
from loguru import logger


class TencentSTTEngine(BaseEngine):
    """腾讯云语音识别引擎"""

    def __init__(
        self,
        app_id: str,
        secret_id: str,
        secret_key: str,
        region: str = "ap-guangzhou",
        sample_rate: int = 16000
    ):
        """
        初始化STT引擎

        Args:
            app_id: 腾讯云应用ID
            secret_id: 腾讯云密钥ID
            secret_key: 腾讯云密钥Key
            region: 地域
            sample_rate: 音频采样率
        """
        self.app_id = app_id
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.sample_rate = sample_rate
        self.client = None

    async def initialize(self):
        """初始化腾讯云客户端"""
        try:
            cred = credential.Credential(self.secret_id, self.secret_key)
            self.client = asr_client.AsrClient(cred, self.region)
            logger.info(f"腾讯云STT引擎已初始化 (区域: {self.region})")

        except Exception as e:
            logger.error(f"初始化腾讯云STT失败: {e}")
            raise

    async def transcribe(self, audio_bytes: bytes, max_retries: int = 3) -> str:
        """
        将音频转换为文字

        Args:
            audio_bytes: 音频数据 (PCM格式)
            max_retries: 最大重试次数

        Returns:
            识别的文本
        """
        if not self.client:
            raise RuntimeError("STT引擎未初始化")

        # 将PCM转为WAV格式
        wav_data = self._pcm_to_wav(audio_bytes)

        for attempt in range(max_retries):
            try:
                # 构造请求
                req = models.SentenceRecognitionRequest()
                req.EngSerViceType = f"{self.sample_rate // 1000}k_zh"
                req.SourceType = 1  # 音频数据
                req.VoiceFormat = "wav"
                req.Data = base64.b64encode(wav_data).decode('utf-8')

                # 发起请求
                logger.debug(f"发起STT请求 (尝试 {attempt + 1}/{max_retries})...")
                resp = self.client.SentenceRecognition(req)

                result = resp.Result
                logger.info(f"🎯 STT识别结果: {result}")

                return result

            except Exception as e:
                logger.warning(f"STT识别失败 (尝试 {attempt + 1}/{max_retries}): {e}")

                if attempt == max_retries - 1:
                    logger.error("STT识别达到最大重试次数")
                    return ""

                # 指数退避
                import asyncio
                await asyncio.sleep(2 ** attempt)

        return ""

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """
        将PCM数据转换为WAV格式

        Args:
            pcm_data: PCM音频数据

        Returns:
            WAV格式音频数据
        """
        wav_buffer = BytesIO()

        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(pcm_data)

        return wav_buffer.getvalue()

    async def cleanup(self):
        """清理资源"""
        self.client = None
        logger.info("STT引擎已清理")
