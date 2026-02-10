"""状态机定义"""
from enum import Enum, auto


class AssistantState(Enum):
    """助理状态枚举"""

    IDLE = auto()           # 待机态 - 监听唤醒词
    LISTENING = auto()      # 监听态 - VAD录音中
    PROCESSING = auto()     # 处理态 - STT+LLM推理中
    SPEAKING = auto()       # 播放态 - TTS播放中
    CONTINUOUS = auto()     # 连续对话窗口 - 等待用户继续说话

    def __str__(self):
        """返回状态的中文描述"""
        state_names = {
            AssistantState.IDLE: "待机",
            AssistantState.LISTENING: "监听中",
            AssistantState.PROCESSING: "思考中",
            AssistantState.SPEAKING: "回复中",
            AssistantState.CONTINUOUS: "等待继续"
        }
        return state_names.get(self, "未知状态")
