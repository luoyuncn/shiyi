"""音频录制器"""
import pyaudio
import numpy as np
from loguru import logger
from typing import Optional


class AudioRecorder:
    """音频录制器 - 管理麦克风输入流"""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        channels: int = 1,
        device_index: Optional[int] = None
    ):
        """
        初始化录音器

        Args:
            sample_rate: 采样率 (Hz)
            chunk_size: 每次读取的帧数
            channels: 声道数 (1=单声道, 2=立体声)
            device_index: 音频设备索引，None表示默认设备
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index

        self.audio = pyaudio.PyAudio()
        self.stream = None

    def start(self):
        """启动录音流"""
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=None
            )

            device_name = "默认设备"
            if self.device_index is not None:
                device_info = self.audio.get_device_info_by_index(self.device_index)
                device_name = device_info.get('name', '未知设备')

            logger.info(f"录音流已启动: {self.sample_rate}Hz, 设备: {device_name}")

        except Exception as e:
            logger.error(f"启动录音流失败: {e}")
            raise

    def read_chunk(self) -> np.ndarray:
        """
        读取一个音频块

        Returns:
            音频数据 (numpy数组, int16格式)
        """
        if not self.stream or not self.stream.is_active():
            raise RuntimeError("录音流未启动或已停止")

        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            return np.frombuffer(data, dtype=np.int16)
        except Exception as e:
            logger.error(f"读取音频数据失败: {e}")
            raise

    def stop(self):
        """停止录音流"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
                logger.info("录音流已停止")
            except Exception as e:
                logger.error(f"停止录音流失败: {e}")

    def cleanup(self):
        """清理资源"""
        self.stop()
        if self.audio:
            self.audio.terminate()
            logger.debug("PyAudio已清理")

    def list_devices(self):
        """列出所有可用的录音设备"""
        logger.info("可用的录音设备:")
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                logger.info(f"  [{i}] {info['name']} (输入通道: {info['maxInputChannels']})")
