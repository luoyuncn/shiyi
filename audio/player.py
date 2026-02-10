"""音频播放器"""
import pyaudio
import asyncio
from loguru import logger
from typing import Optional


class AudioPlayer:
    """音频播放器 - 管理扬声器输出流"""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        device_index: Optional[int] = None
    ):
        """
        初始化播放器

        Args:
            sample_rate: 采样率 (Hz)
            channels: 声道数
            device_index: 音频设备索引，None表示默认设备
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index

        self.audio = pyaudio.PyAudio()
        self.stream = None

    def start(self):
        """启动播放流"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.device_index
            )

            device_name = "默认设备"
            if self.device_index is not None:
                device_info = self.audio.get_device_info_by_index(self.device_index)
                device_name = device_info.get('name', '未知设备')

            logger.info(f"播放流已启动: {self.sample_rate}Hz, 设备: {device_name}")

        except Exception as e:
            logger.error(f"启动播放流失败: {e}")
            raise

    async def play_audio(self, audio_data: bytes):
        """
        异步播放音频数据

        Args:
            audio_data: 音频数据 (bytes格式)
        """
        if not self.stream or not self.stream.is_active():
            raise RuntimeError("播放流未启动或已停止")

        try:
            # 分块播放避免阻塞事件循环
            chunk_size = 4096
            total_chunks = (len(audio_data) + chunk_size - 1) // chunk_size

            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                self.stream.write(chunk)

                # 让出控制权，避免阻塞
                if i % (chunk_size * 10) == 0:
                    await asyncio.sleep(0)

            logger.debug(f"播放完成: {len(audio_data)} bytes ({total_chunks} chunks)")

        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            raise

    def stop(self):
        """停止播放流"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                logger.info("播放流已停止")
            except Exception as e:
                logger.error(f"停止播放流失败: {e}")

    def cleanup(self):
        """清理资源"""
        self.stop()
        if self.audio:
            self.audio.terminate()
            logger.debug("PyAudio已清理")

    def list_devices(self):
        """列出所有可用的播放设备"""
        logger.info("可用的播放设备:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxOutputChannels'] > 0:
                logger.info(f"  [{i}] {info['name']} (输出通道: {info['maxOutputChannels']})")
