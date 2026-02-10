# 🏠 小跟班 - 私人语音助理 V1.0

基于树莓派4B的智能语音助手，支持本地唤醒词、流式对话和自动连续对话。

## ✨ 功能特性

- ✅ **本地唤醒词检测** - 使用 openWakeWord，无需联网，保护隐私
- ✅ **智能VAD录音** - Silero VAD 自动检测静音，精准切断录音
- ✅ **高质量语音识别** - 腾讯云一句话识别，中文识别准确度高
- ✅ **流式对话** - LLM逐句生成，TTS实时合成，延迟 < 2秒
- ✅ **自动连续对话** - 回答完成后自动进入3秒监听窗口
- ✅ **模块化架构** - 所有引擎可插拔替换

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) 包管理工具
- 稳定的网络连接（用于云端API）

### 2. 安装依赖

```bash
# 安装 uv（如果还没有）
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/Mac
curl -LsSf https://astral.sh/uv/install.sh | sh

# 克隆项目
git clone <your-repo-url> tui-assistant
cd tui-assistant

# 创建虚拟环境并安装依赖
uv venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

# 安装项目依赖
uv pip install -e .
```

### 3. 配置API密钥

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的API密钥
# Windows
notepad .env
# Linux/Mac
nano .env
```

需要配置的密钥：
- **腾讯云** - [获取地址](https://console.cloud.tencent.com/cam/capi)
  - `TENCENT_APP_ID`
  - `TENCENT_SECRET_ID`
  - `TENCENT_SECRET_KEY`

- **DeepSeek** - [获取地址](https://platform.deepseek.com/api_keys)
  - `DEEPSEEK_API_KEY`

### 4. 运行

```bash
python main.py
```

## 📖 使用指南

### 基础对话

1. 程序启动后，等待唤醒词
2. 说出唤醒词（默认预训练模型）
3. 听到提示音后开始说话
4. 停顿500ms后自动识别
5. 助理开始回答

### 连续对话

- 助理回答完成后，会自动进入3秒监听窗口
- 直接继续说话，无需再次说唤醒词
- 3秒内无声音，自动回到待机状态

### 退出程序

按 `Ctrl+C` 优雅退出

## 🛠️ 配置说明

主配置文件：`config/config.yaml`

### 关键配置项

```yaml
# 系统配置
system:
  log_level: "INFO"  # 日志级别: DEBUG/INFO/WARNING/ERROR

# 唤醒词配置
wake_word:
  threshold: 0.5  # 检测阈值，越高越严格

# VAD配置
vad:
  silence_duration_ms: 500  # 静音判定时长
  continuous_window_seconds: 3  # 连续对话窗口

# LLM配置
llm:
  model: "deepseek-chat"  # 模型名称
  temperature: 0.7  # 温度参数
  system_prompt: |  # 系统提示词
    你是"小跟班"...

# TTS配置
tts:
  voice: "zh-CN-YunxiNeural"  # 语音角色
  rate: "+0%"  # 语速调整
```

## 📂 项目结构

```
tui-assistant/
├── config/              # 配置管理
│   ├── config.yaml     # 主配置文件
│   └── settings.py     # 配置加载器
├── core/               # 核心控制逻辑
│   ├── assistant.py    # 主控制器
│   ├── state_machine.py # 状态机
│   └── sentence_splitter.py # 句子切分器
├── engines/            # AI引擎实现
│   ├── wake_word/      # 唤醒词引擎
│   ├── vad/           # VAD引擎
│   ├── stt/           # 语音识别
│   ├── llm/           # 大语言模型
│   └── tts/           # 语音合成
├── audio/             # 音频处理
│   ├── recorder.py    # 录音器
│   └── player.py      # 播放器
├── utils/             # 工具函数
│   └── logger.py      # 日志配置
├── main.py            # 程序入口
└── pyproject.toml     # 依赖管理
```

## 🎯 技术栈

| 模块 | 技术选型 | 说明 |
|------|---------|------|
| 唤醒词 | openWakeWord | 本地实时检测 |
| VAD | Silero VAD | 高精度语音检测 |
| STT | 腾讯云 | 中文识别准确 |
| LLM | DeepSeek | 性价比高 |
| TTS | Edge-TTS | 免费，音质好 |
| 包管理 | uv | 快速，现代化 |

## 🔧 故障排除

### PyAudio安装失败

**Windows:**
```bash
# 下载预编译wheel
# 访问: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
uv pip install PyAudio‑0.2.14‑cpXX‑cpXX‑win_amd64.whl
```

**Linux:**
```bash
sudo apt install portaudio19-dev python3-pyaudio
uv pip install pyaudio
```

**Mac:**
```bash
brew install portaudio
uv pip install pyaudio
```

### 找不到音频设备

运行诊断脚本：
```python
from audio.recorder import AudioRecorder
recorder = AudioRecorder()
recorder.list_devices()
```

在 `config/config.yaml` 中指定设备索引：
```yaml
audio:
  input_device_index: 1  # 你的麦克风索引
  output_device_index: 2  # 你的扬声器索引
```

### API调用失败

1. 检查 `.env` 文件配置是否正确
2. 检查网络连接
3. 查看 `logs/` 目录下的日志文件

## 🚀 部署到树莓派

详细部署步骤见：[docs/implementation-plan.md](docs/implementation-plan.md) 的"部署到树莓派"章节

## 📈 后续优化方向

- [ ] 使用本地Whisper替代云端STT
- [ ] 部署本地小模型降低延迟
- [ ] 添加打断功能
- [ ] 实现Function Calling控制GPIO
- [ ] 添加长期记忆（Vector DB）
- [ ] LED状态指示灯
- [ ] 自定义唤醒词训练

## 📄 许可证

MIT License

## 🙏 致谢

- [openWakeWord](https://github.com/dscripka/openWakeWord)
- [Silero VAD](https://github.com/snakers4/silero-vad)
- [Edge-TTS](https://github.com/rany2/edge-tts)
- [uv](https://github.com/astral-sh/uv)

---

**祝你使用愉快！有问题欢迎提Issue。** 🎉
