# 🚀 "小跟班" V1.0 详细实施计划

---

## 📋 开发阶段概览

本实施计划将开发分为 **5个阶段**，每个阶段都可以独立验证功能：

| 阶段 | 目标 | 预计耗时 | 验证标准 |
|------|------|----------|----------|
| **阶段1** | 项目搭建 + 音频基础 | 1天 | 能录音和播放 |
| **阶段2** | 唤醒词 + VAD | 1-2天 | 能识别唤醒词并录音 |
| **阶段3** | STT + LLM + TTS | 2天 | 能完成完整对话 |
| **阶段4** | 流式优化 | 1-2天 | 延迟降至2秒内 |
| **阶段5** | 连续对话 + 优化 | 1天 | 支持自动连续对话 |

**总预计耗时**: 6-8天

---

## 🔧 阶段1: 项目搭建 + 音频基础

### 目标
搭建完整的项目结构，实现基础的音频录制和播放功能。

### 任务清单

#### 1.1 初始化项目
```bash
# 创建项目目录
cd tui-assistant

# 初始化uv项目
uv init
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 创建目录结构
mkdir -p config core engines/{wake_word,vad,stt,llm,tts} audio utils models logs tests docs
touch config/{__init__.py,settings.py,config.yaml}
touch core/{__init__.py,assistant.py,state_machine.py,sentence_splitter.py}
touch engines/__init__.py engines/base.py
touch audio/{__init__.py,recorder.py,player.py}
touch utils/{__init__.py,logger.py,audio_utils.py}
touch main.py .env.example .gitignore
```

#### 1.2 编写 pyproject.toml
```toml
[project]
name = "tui-assistant"
version = "1.0.0"
description = "私人语音助理'小跟班'"
requires-python = ">=3.10"
dependencies = [
    "pyaudio>=0.2.14",
    "numpy>=1.24.0",
    "openwakeword>=0.5.0",
    "silero-vad>=4.0.0",
    "tencentcloud-sdk-python>=3.0.0",
    "openai>=1.12.0",
    "edge-tts>=6.1.0",
    "pyyaml>=6.0.1",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "loguru>=0.7.2",
    "aiofiles>=23.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.2.0",
]
```

#### 1.3 安装依赖
```bash
uv pip install -e .
uv pip install -e ".[dev]"
```

#### 1.4 实现基础音频模块

**audio/recorder.py** - 音频录制器
```python
import pyaudio
import numpy as np
from loguru import logger

class AudioRecorder:
    """音频录制器"""

    def __init__(self, sample_rate=16000, chunk_size=1024, channels=1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.audio = pyaudio.PyAudio()
        self.stream = None

    def start(self, device_index=None):
        """开始录音流"""
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=device_index,
            frames_per_buffer=self.chunk_size
        )
        logger.info(f"录音流已启动: {self.sample_rate}Hz")

    def read_chunk(self) -> np.ndarray:
        """读取一个音频块"""
        data = self.stream.read(self.chunk_size, exception_on_overflow=False)
        return np.frombuffer(data, dtype=np.int16)

    def stop(self):
        """停止录音"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        logger.info("录音流已停止")

    def cleanup(self):
        """清理资源"""
        self.stop()
        self.audio.terminate()
```

**audio/player.py** - 音频播放器
```python
import pyaudio
import asyncio
from loguru import logger

class AudioPlayer:
    """音频播放器"""

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.audio = pyaudio.PyAudio()
        self.stream = None

    def start(self, device_index=None):
        """启动播放流"""
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            output=True,
            output_device_index=device_index
        )
        logger.info(f"播放流已启动: {self.sample_rate}Hz")

    async def play_audio(self, audio_data: bytes):
        """异步播放音频"""
        if not self.stream:
            raise RuntimeError("播放流未启动")

        # 分块播放避免阻塞
        chunk_size = 1024
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i+chunk_size]
            self.stream.write(chunk)
            await asyncio.sleep(0)  # 让出控制权

        logger.debug(f"播放完成: {len(audio_data)} bytes")

    def stop(self):
        """停止播放"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        logger.info("播放流已停止")

    def cleanup(self):
        """清理资源"""
        self.stop()
        self.audio.terminate()
```

#### 1.5 编写测试代码

**tests/test_audio.py**
```python
import asyncio
import pytest
from audio.recorder import AudioRecorder
from audio.player import AudioPlayer

@pytest.mark.asyncio
async def test_record_and_play():
    """测试录音和播放"""
    recorder = AudioRecorder()
    player = AudioPlayer()

    try:
        # 录音3秒
        recorder.start()
        chunks = []
        for _ in range(int(3 * 16000 / 1024)):
            chunk = recorder.read_chunk()
            chunks.append(chunk.tobytes())
        recorder.stop()

        # 播放录音
        player.start()
        audio_data = b''.join(chunks)
        await player.play_audio(audio_data)
        player.stop()

        assert len(audio_data) > 0

    finally:
        recorder.cleanup()
        player.cleanup()
```

### 验证标准
运行测试，确保能正常录音3秒并播放出来：
```bash
pytest tests/test_audio.py -v
```

---

## 🎤 阶段2: 唤醒词 + VAD

### 目标
实现唤醒词检测和语音活动检测，能够在说"小跟班"后自动开始录音，并在静音时停止。

### 任务清单

#### 2.1 实现基础引擎接口

**engines/base.py**
```python
from abc import ABC, abstractmethod

class BaseEngine(ABC):
    """所有引擎的基类"""

    @abstractmethod
    async def initialize(self):
        """异步初始化"""
        pass

    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        pass
```

#### 2.2 实现唤醒词引擎

**engines/wake_word/openwakeword_engine.py**
```python
import numpy as np
from openwakeword import Model
from engines.base import BaseEngine
from loguru import logger

class OpenWakeWordEngine(BaseEngine):
    """OpenWakeWord唤醒词引擎"""

    def __init__(self, model_path: str, threshold: float = 0.5):
        self.model_path = model_path
        self.threshold = threshold
        self.model = None

    async def initialize(self):
        """加载模型"""
        # 如果没有自定义模型，使用预训练模型
        self.model = Model(wakeword_models=[self.model_path] if self.model_path else None)
        logger.info(f"唤醒词模型已加载: {self.model_path or 'default'}")

    async def detect(self, audio_chunk: np.ndarray) -> bool:
        """检测唤醒词"""
        # 预测
        prediction = self.model.predict(audio_chunk)

        # 检查所有模型的预测结果
        for model_name, score in prediction.items():
            if score >= self.threshold:
                logger.info(f"检测到唤醒词: {model_name} (置信度: {score:.2f})")
                return True
        return False

    async def cleanup(self):
        """清理资源"""
        self.model = None
        logger.info("唤醒词引擎已清理")
```

#### 2.3 实现VAD引擎

**engines/vad/silero_vad_engine.py**
```python
import torch
import numpy as np
from io import BytesIO
from engines.base import BaseEngine
from audio.recorder import AudioRecorder
from loguru import logger
import asyncio

class SileroVADEngine(BaseEngine):
    """Silero VAD引擎"""

    def __init__(self,
                 recorder: AudioRecorder,
                 silence_duration_ms: int = 500,
                 max_recording_seconds: int = 10):
        self.recorder = recorder
        self.silence_duration_ms = silence_duration_ms
        self.max_recording_seconds = max_recording_seconds
        self.model = None
        self.sample_rate = recorder.sample_rate

    async def initialize(self):
        """加载Silero VAD模型"""
        self.model, utils = torch.hub.load(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False
        )
        logger.info("Silero VAD模型已加载")

    async def record_until_silence(self) -> bytes:
        """录音直到检测到静音"""
        buffer = BytesIO()
        silence_chunks = 0
        max_chunks = int(self.max_recording_seconds * self.sample_rate / self.recorder.chunk_size)
        silence_threshold = int(self.silence_duration_ms / 1000 * self.sample_rate / self.recorder.chunk_size)

        logger.info("开始录音...")

        for i in range(max_chunks):
            chunk = self.recorder.read_chunk()
            buffer.write(chunk.tobytes())

            # VAD检测
            audio_float = chunk.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float)
            speech_prob = self.model(audio_tensor, self.sample_rate).item()

            # 判断是否为静音
            if speech_prob < 0.5:
                silence_chunks += 1
                if silence_chunks >= silence_threshold:
                    logger.info(f"检测到{self.silence_duration_ms}ms静音，停止录音")
                    break
            else:
                silence_chunks = 0

            await asyncio.sleep(0)  # 让出控制权

        audio_bytes = buffer.getvalue()
        logger.info(f"录音完成: {len(audio_bytes)} bytes")
        return audio_bytes

    async def listen_with_timeout(self, timeout: float = 3.0) -> bool:
        """连续对话窗口：timeout秒内是否检测到人声"""
        start_time = asyncio.get_event_loop().time()
        chunk_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            chunk = self.recorder.read_chunk()

            # VAD检测
            audio_float = chunk.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float)
            speech_prob = self.model(audio_tensor, self.sample_rate).item()

            if speech_prob >= 0.5:
                logger.info("连续对话窗口检测到人声")
                return True

            await asyncio.sleep(0)

        logger.info("连续对话窗口超时，未检测到人声")
        return False

    async def cleanup(self):
        """清理资源"""
        self.model = None
        logger.info("VAD引擎已清理")
```

#### 2.4 编写状态机

**core/state_machine.py**
```python
from enum import Enum, auto

class AssistantState(Enum):
    """助理状态枚举"""
    IDLE = auto()           # 待机态
    LISTENING = auto()      # 监听态（录音中）
    PROCESSING = auto()     # 处理态（STT+LLM+TTS）
    SPEAKING = auto()       # 播放态
    CONTINUOUS = auto()     # 连续对话窗口
```

### 验证标准
编写测试程序验证唤醒词和VAD：
```python
# tests/test_wake_vad.py
import asyncio
from audio.recorder import AudioRecorder
from engines.wake_word.openwakeword_engine import OpenWakeWordEngine
from engines.vad.silero_vad_engine import SileroVADEngine

async def test_wake_and_record():
    recorder = AudioRecorder()
    wake_engine = OpenWakeWordEngine(model_path=None, threshold=0.5)
    vad_engine = SileroVADEngine(recorder)

    await wake_engine.initialize()
    await vad_engine.initialize()

    recorder.start()

    print("等待唤醒词...")
    while True:
        chunk = recorder.read_chunk()
        if await wake_engine.detect(chunk):
            print("检测到唤醒词！开始录音...")
            audio_data = await vad_engine.record_until_silence()
            print(f"录音完成: {len(audio_data)} bytes")
            break
        await asyncio.sleep(0)

    recorder.cleanup()
    await wake_engine.cleanup()
    await vad_engine.cleanup()

if __name__ == "__main__":
    asyncio.run(test_wake_and_record())
```

---

## 🔄 阶段3: STT + LLM + TTS 完整对话

### 目标
实现完整的对话流程：语音→文字→大模型→语音，能够完成一轮对话。

### 任务清单

#### 3.1 实现配置管理

**config/config.yaml**
```yaml
system:
  name: "小跟班"
  log_level: "INFO"

wake_word:
  engine: "openwakeword"
  model_path: null
  threshold: 0.5

vad:
  silence_duration_ms: 500
  max_recording_seconds: 10
  continuous_window_seconds: 3

stt:
  app_id: "${TENCENT_APP_ID}"
  secret_id: "${TENCENT_SECRET_ID}"
  secret_key: "${TENCENT_SECRET_KEY}"
  region: "ap-guangzhou"

llm:
  api_base: "https://api.deepseek.com/v1"
  api_key: "${DEEPSEEK_API_KEY}"
  model: "deepseek-chat"
  temperature: 0.7
  max_tokens: 500
  stream: true
  system_prompt: |
    你是"小跟班"，腿哥的私人智能助理。
    你的性格：聪明、高效、略带幽默。
    回答要求：简洁明了，口语化，每句话控制在30字以内。

tts:
  voice: "zh-CN-YunxiNeural"
  rate: "+0%"
```

**config/settings.py**
```python
from pydantic import BaseModel
from pydantic_settings import BaseSettings
import yaml
import os
from pathlib import Path

class STTConfig(BaseModel):
    app_id: str
    secret_id: str
    secret_key: str
    region: str = "ap-guangzhou"

class LLMConfig(BaseModel):
    api_base: str
    api_key: str
    model: str
    temperature: float = 0.7
    max_tokens: int = 500
    stream: bool = True
    system_prompt: str

class TTSConfig(BaseModel):
    voice: str
    rate: str = "+0%"

class Settings(BaseSettings):
    stt: STTConfig
    llm: LLMConfig
    tts: TTSConfig

    class Config:
        env_file = ".env"

def load_config(config_path: str = "config/config.yaml") -> Settings:
    """加载配置并替换环境变量"""
    with open(config_path, 'r', encoding='utf-8') as f:
        config_text = f.read()

    # 替换环境变量
    import re
    def replace_env(match):
        var_name = match.group(1)
        return os.getenv(var_name, "")

    config_text = re.sub(r'\$\{(\w+)\}', replace_env, config_text)
    config_dict = yaml.safe_load(config_text)

    return Settings(**config_dict)
```

**.env.example**
```bash
# 腾讯云配置
TENCENT_APP_ID=your_app_id
TENCENT_SECRET_ID=your_secret_id
TENCENT_SECRET_KEY=your_secret_key

# DeepSeek API
DEEPSEEK_API_KEY=sk-xxxxx
```

#### 3.2 实现STT引擎

**engines/stt/tencent_stt_engine.py**
```python
import base64
import json
from tencentcloud.common import credential
from tencentcloud.asr.v20190614 import asr_client, models
from engines.base import BaseEngine
from loguru import logger

class TencentSTTEngine(BaseEngine):
    """腾讯云一句话识别引擎"""

    def __init__(self, app_id: str, secret_id: str, secret_key: str, region: str = "ap-guangzhou"):
        self.app_id = app_id
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.client = None

    async def initialize(self):
        """初始化客户端"""
        cred = credential.Credential(self.secret_id, self.secret_key)
        self.client = asr_client.AsrClient(cred, self.region)
        logger.info("腾讯云STT引擎已初始化")

    async def transcribe(self, audio_bytes: bytes) -> str:
        """音频转文字"""
        try:
            # 构造请求
            req = models.SentenceRecognitionRequest()
            req.EngSerViceType = "16k_zh"
            req.SourceType = 1
            req.VoiceFormat = "wav"
            req.DataLen = len(audio_bytes)
            req.Data = base64.b64encode(audio_bytes).decode('utf-8')

            # 发起请求
            resp = self.client.SentenceRecognition(req)
            result = resp.Result

            logger.info(f"STT结果: {result}")
            return result

        except Exception as e:
            logger.error(f"STT识别失败: {e}")
            return ""

    async def cleanup(self):
        """清理资源"""
        self.client = None
        logger.info("STT引擎已清理")
```

#### 3.3 实现LLM引擎

**engines/llm/openai_compatible_engine.py**
```python
from openai import AsyncOpenAI
from engines.base import BaseEngine
from loguru import logger

class OpenAICompatibleEngine(BaseEngine):
    """OpenAI协议兼容的LLM引擎"""

    def __init__(self, api_base: str, api_key: str, model: str,
                 system_prompt: str, temperature: float = 0.7):
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.client = None
        self.conversation_history = []

    async def initialize(self):
        """初始化客户端"""
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
        logger.info(f"LLM引擎已初始化: {self.model}")

    async def chat_stream(self, message: str):
        """流式对话"""
        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": message})

        # 构造消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history
        ]

        # 流式请求
        full_response = ""
        async for chunk in await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            stream=True
        ):
            if chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_response += token
                yield token

        # 添加助手回复到历史
        self.conversation_history.append({"role": "assistant", "content": full_response})
        logger.info(f"LLM回复: {full_response}")

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []

    async def cleanup(self):
        """清理资源"""
        await self.client.close()
        logger.info("LLM引擎已清理")
```

#### 3.4 实现TTS引擎

**engines/tts/edge_tts_engine.py**
```python
import edge_tts
from engines.base import BaseEngine
from loguru import logger

class EdgeTTSEngine(BaseEngine):
    """Edge-TTS引擎"""

    def __init__(self, voice: str = "zh-CN-YunxiNeural", rate: str = "+0%"):
        self.voice = voice
        self.rate = rate

    async def initialize(self):
        """初始化"""
        logger.info(f"Edge-TTS引擎已初始化: {self.voice}")

    async def synthesize_stream(self, text: str):
        """流式合成语音"""
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

        logger.debug(f"TTS合成完成: {text[:20]}...")

    async def cleanup(self):
        """清理资源"""
        logger.info("TTS引擎已清理")
```

### 验证标准
编写完整对话测试：
```python
# tests/test_full_conversation.py
import asyncio
from config.settings import load_config
from engines.stt.tencent_stt_engine import TencentSTTEngine
from engines.llm.openai_compatible_engine import OpenAICompatibleEngine
from engines.tts.edge_tts_engine import EdgeTTSEngine
from audio.player import AudioPlayer

async def test_conversation():
    config = load_config()

    # 初始化引擎
    stt = TencentSTTEngine(**config.stt.model_dump())
    llm = OpenAICompatibleEngine(**config.llm.model_dump())
    tts = EdgeTTSEngine(**config.tts.model_dump())
    player = AudioPlayer()

    await stt.initialize()
    await llm.initialize()
    await tts.initialize()
    player.start()

    # 测试对话
    test_audio = b"..."  # 录音数据

    # STT
    text = await stt.transcribe(test_audio)
    print(f"识别: {text}")

    # LLM
    response = ""
    async for token in llm.chat_stream(text):
        response += token
        print(token, end="", flush=True)

    # TTS
    audio_chunks = []
    async for chunk in tts.synthesize_stream(response):
        audio_chunks.append(chunk)

    # 播放
    await player.play_audio(b''.join(audio_chunks))

    # 清理
    player.cleanup()
    await stt.cleanup()
    await llm.cleanup()
    await tts.cleanup()

if __name__ == "__main__":
    asyncio.run(test_conversation())
```

---

## ⚡ 阶段4: 流式优化

### 目标
实现LLM → TTS的流式处理，将延迟从3-4秒降至1-2秒。

### 任务清单

#### 4.1 实现句子切分器

**core/sentence_splitter.py**
```python
import re
from loguru import logger

class SentenceSplitter:
    """句子切分器 - 按标点符号切分完整句子"""

    # 中文句子结束标点
    SENTENCE_ENDINGS = ['。', '！', '?', '；', '…']

    def __init__(self):
        self.buffer = ""

    def add_token(self, token: str) -> str | None:
        """
        添加token，如果形成完整句子则返回

        Args:
            token: LLM生成的token

        Returns:
            完整句子或None
        """
        self.buffer += token

        # 检查是否包含句子结束标点
        for ending in self.SENTENCE_ENDINGS:
            if ending in self.buffer:
                # 找到第一个结束标点的位置
                idx = self.buffer.index(ending)
                sentence = self.buffer[:idx+1].strip()
                self.buffer = self.buffer[idx+1:]

                if sentence:
                    logger.debug(f"切分出句子: {sentence}")
                    return sentence

        return None

    def flush(self) -> str | None:
        """
        刷新缓冲区，返回剩余内容

        Returns:
            剩余文本或None
        """
        if self.buffer.strip():
            sentence = self.buffer.strip()
            self.buffer = ""
            logger.debug(f"刷新剩余: {sentence}")
            return sentence
        return None

    def reset(self):
        """重置缓冲区"""
        self.buffer = ""
```

#### 4.2 实现流式处理主逻辑

**core/assistant.py (核心部分)**
```python
import asyncio
from loguru import logger
from core.state_machine import AssistantState
from core.sentence_splitter import SentenceSplitter

class AssistantCore:
    """助理核心控制器"""

    def __init__(self, config):
        self.config = config
        self.state = AssistantState.IDLE

        # 引擎（待初始化）
        self.wake_engine = None
        self.vad_engine = None
        self.stt_engine = None
        self.llm_engine = None
        self.tts_engine = None
        self.recorder = None
        self.player = None

        # 句子队列：LLM生成的句子传递给TTS
        self.sentence_queue = asyncio.Queue()

    async def start(self):
        """启动助理"""
        # 初始化所有引擎...
        logger.info("小跟班已启动")

        # 启动两个并发任务
        await asyncio.gather(
            self._wake_and_listen_loop(),  # 监听和处理
            self._tts_playback_loop()      # TTS播放
        )

    async def _wake_and_listen_loop(self):
        """唤醒和监听循环"""
        while True:
            if self.state == AssistantState.IDLE:
                # 等待唤醒词
                chunk = self.recorder.read_chunk()
                if await self.wake_engine.detect(chunk):
                    logger.info("唤醒！")
                    self.state = AssistantState.LISTENING

            elif self.state == AssistantState.LISTENING:
                # VAD录音
                audio_data = await self.vad_engine.record_until_silence()
                self.state = AssistantState.PROCESSING

                # STT
                text = await self.stt_engine.transcribe(audio_data)
                logger.info(f"用户: {text}")

                # LLM流式生成 + 句子切分
                await self._stream_llm_to_tts(text)

                # 等待TTS播放完成（通过队列空和状态判断）
                await self.sentence_queue.join()

                # 进入连续对话窗口
                self.state = AssistantState.CONTINUOUS

            elif self.state == AssistantState.CONTINUOUS:
                # 3秒窗口检测人声
                has_speech = await self.vad_engine.listen_with_timeout(3.0)
                if has_speech:
                    # 继续对话
                    self.state = AssistantState.LISTENING
                else:
                    # 回到待机
                    self.state = AssistantState.IDLE
                    logger.info("回到待机状态")

            await asyncio.sleep(0.01)

    async def _stream_llm_to_tts(self, user_message: str):
        """LLM流式生成 + 句子切分 + 送入TTS队列"""
        splitter = SentenceSplitter()

        async for token in self.llm_engine.chat_stream(user_message):
            # 尝试切分句子
            sentence = splitter.add_token(token)
            if sentence:
                # 将完整句子放入队列
                await self.sentence_queue.put(sentence)

        # 刷新剩余内容
        remaining = splitter.flush()
        if remaining:
            await self.sentence_queue.put(remaining)

        # 发送结束信号
        await self.sentence_queue.put(None)

    async def _tts_playback_loop(self):
        """TTS播放循环"""
        while True:
            # 从队列获取句子
            sentence = await self.sentence_queue.get()

            if sentence is None:
                # 结束信号
                self.sentence_queue.task_done()
                continue

            # TTS合成
            audio_chunks = []
            async for chunk in self.tts_engine.synthesize_stream(sentence):
                audio_chunks.append(chunk)

            # 播放
            self.state = AssistantState.SPEAKING
            await self.player.play_audio(b''.join(audio_chunks))

            self.sentence_queue.task_done()
```

### 验证标准
测试流式处理的延迟：
- 从说话结束到第一句话播放应 < 2秒
- 使用秒表或日志时间戳验证

---

## 🔁 阶段5: 连续对话 + 优化

### 目标
完善连续对话功能，添加日志、异常处理和优化。

### 任务清单

#### 5.1 完善日志系统

**utils/logger.py**
```python
from loguru import logger
import sys

def setup_logger(log_level: str = "INFO"):
    """配置日志系统"""
    logger.remove()  # 移除默认处理器

    # 控制台输出
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )

    # 文件输出
    logger.add(
        "logs/assistant_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:8} | {name}:{function}:{line} - {message}"
    )

    logger.info("日志系统已初始化")
```

#### 5.2 添加异常处理

在各个引擎中添加重试逻辑：
```python
# 示例：STT引擎重试
async def transcribe(self, audio_bytes: bytes, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            # ... 识别逻辑
            return result
        except Exception as e:
            logger.warning(f"STT识别失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
```

#### 5.3 完善main.py

**main.py**
```python
import asyncio
from loguru import logger
from config.settings import load_config
from utils.logger import setup_logger
from core.assistant import AssistantCore

async def main():
    """程序入口"""
    # 加载配置
    config = load_config()

    # 设置日志
    setup_logger(config.system.get("log_level", "INFO"))

    # 初始化助理
    assistant = AssistantCore(config)

    try:
        logger.info("=" * 50)
        logger.info("🏠 小跟班私人助理 V1.0")
        logger.info("=" * 50)
        await assistant.start()

    except KeyboardInterrupt:
        logger.info("\n接收到退出信号 (Ctrl+C)")

    except Exception as e:
        logger.exception(f"程序异常退出: {e}")

    finally:
        await assistant.cleanup()
        logger.info("小跟班已关闭，再见！")

if __name__ == "__main__":
    asyncio.run(main())
```

#### 5.4 编写README

**README.md**
```markdown
# 🏠 小跟班 - 私人语音助理 V1.0

基于树莓派4B的智能语音助手，支持唤醒词、流式对话和连续对话。

## 快速开始

### 1. 安装依赖

\`\`\`bash
# 安装uv（如果还没有）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone <your-repo>
cd tui-assistant

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate
uv pip install -e .
\`\`\`

### 2. 配置环境变量

\`\`\`bash
cp .env.example .env
# 编辑.env，填入你的API密钥
\`\`\`

### 3. 运行

\`\`\`bash
python main.py
\`\`\`

## 功能特性

- ✅ 本地唤醒词检测（openWakeWord）
- ✅ 智能VAD录音（Silero VAD）
- ✅ 腾讯云语音识别
- ✅ DeepSeek大模型对话
- ✅ Edge-TTS语音合成
- ✅ 流式处理（延迟<2秒）
- ✅ 自动连续对话

## 项目结构

见 `docs/implementation-plan.md`

## 许可证

MIT
\`\`\`

### 验证标准
- 完整运行一次对话流程
- 测试连续对话（3秒内继续说话）
- 查看日志文件是否正常记录

---

## 📦 部署到树莓派

### 系统要求
- Raspberry Pi 4B (4GB/8GB RAM)
- Raspberry Pi OS (Debian Bullseye 64-bit)
- Python 3.10+
- 稳定WiFi连接

### 部署步骤

#### 1. 安装系统依赖
\`\`\`bash
sudo apt update
sudo apt install -y python3-pip python3-venv portaudio19-dev git

# 安装uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
\`\`\`

#### 2. 克隆并配置项目
\`\`\`bash
cd ~
git clone <your-repo> tui-assistant
cd tui-assistant

uv venv
source .venv/bin/activate
uv pip install -e .

cp .env.example .env
nano .env  # 填入API密钥
\`\`\`

#### 3. 配置音频设备
\`\`\`bash
# 查看音频设备
arecord -l   # 录音设备
aplay -l     # 播放设备

# 测试麦克风
arecord -d 5 test.wav
aplay test.wav
\`\`\`

#### 4. 设置开机自启（可选）
\`\`\`bash
# 创建systemd服务
sudo nano /etc/systemd/system/xiaogenban.service
\`\`\`

内容：
\`\`\`ini
[Unit]
Description=Xiao Gen Ban Personal Assistant
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/tui-assistant
Environment="PATH=/home/pi/tui-assistant/.venv/bin"
ExecStart=/home/pi/tui-assistant/.venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
\`\`\`

启动服务：
\`\`\`bash
sudo systemctl enable xiaogenban
sudo systemctl start xiaogenban
sudo systemctl status xiaogenban
\`\`\`

---

## 🔍 常见问题

### 1. PyAudio安装失败
\`\`\`bash
sudo apt install portaudio19-dev
uv pip install pyaudio
\`\`\`

### 2. 麦克风无法录音
检查权限：
\`\`\`bash
sudo usermod -a -G audio $USER
\`\`\`

### 3. API调用失败
- 检查.env配置是否正确
- 检查网络连接
- 查看logs目录下的日志

---

## 📈 后续优化方向

1. **性能优化**
   - 使用本地Whisper替代腾讯云STT
   - 部署本地小模型（如Qwen-7B）降低延迟

2. **功能扩展**
   - 添加长期记忆（Vector DB）
   - 实现Function Calling控制GPIO
   - 支持打断功能

3. **体验优化**
   - LED状态指示灯
   - 音频降噪算法
   - 多唤醒词支持

---

## 🎯 总结

本实施计划提供了从0到1构建"小跟班"私人助理的完整路径：

- **第1阶段**: 搭建基础框架和音频模块
- **第2阶段**: 实现唤醒和录音功能
- **第3阶段**: 打通完整对话流程
- **第4阶段**: 优化为流式处理
- **第5阶段**: 完善连续对话和生产特性

每个阶段都有明确的验证标准，可以逐步推进。预计6-8天完成MVP版本。

**祝你开发顺利！有问题随时沟通。** 🚀
