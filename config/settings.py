"""配置加载器"""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
import os
import re
from pathlib import Path
from typing import Optional


class SystemConfig(BaseModel):
    """系统配置"""
    name: str = "小跟班"
    log_level: str = "INFO"
    audio_sample_rate: int = 16000


class WakeWordConfig(BaseModel):
    """唤醒词配置"""
    engine: str = "openwakeword"
    model_path: Optional[str] = None
    threshold: float = 0.5


class VADConfig(BaseModel):
    """VAD配置"""
    engine: str = "silero"
    silence_duration_ms: int = 500
    max_recording_seconds: int = 10
    continuous_window_seconds: int = 3


class STTConfig(BaseModel):
    """语音识别配置"""
    engine: str = "tencent"
    app_id: str
    secret_id: str
    secret_key: str
    region: str = "ap-guangzhou"


class LLMConfig(BaseModel):
    """大语言模型配置"""
    engine: str = "openai_compatible"
    api_base: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 500
    stream: bool = True
    system_prompt: str


class TTSConfig(BaseModel):
    """语音合成配置"""
    engine: str = "edge"
    voice: str
    rate: str = "+0%"
    pitch: str = "+0Hz"


class AudioConfig(BaseModel):
    """音频设备配置"""
    input_device_index: Optional[int] = None
    output_device_index: Optional[int] = None
    chunk_size: int = 1024


class Settings(BaseModel):
    """完整配置"""
    system: SystemConfig
    wake_word: WakeWordConfig
    vad: VADConfig
    stt: STTConfig
    llm: LLMConfig
    tts: TTSConfig
    audio: AudioConfig


def load_config(config_path: str = "config/config.yaml") -> Settings:
    """
    加载配置文件并替换环境变量

    Args:
        config_path: 配置文件路径

    Returns:
        Settings对象
    """
    # 读取配置文件
    with open(config_path, 'r', encoding='utf-8') as f:
        config_text = f.read()

    # 替换环境变量 ${VAR_NAME}
    def replace_env(match):
        var_name = match.group(1)
        value = os.getenv(var_name)
        if value is None:
            raise ValueError(f"环境变量 {var_name} 未设置，请检查.env文件")
        return value

    config_text = re.sub(r'\$\{(\w+)\}', replace_env, config_text)

    # 解析YAML
    config_dict = yaml.safe_load(config_text)

    # 创建Settings对象
    return Settings(**config_dict)
