"""OpenAI协议兼容的大语言模型引擎"""
from openai import AsyncOpenAI
from engines.base import BaseEngine
from loguru import logger
from typing import AsyncGenerator, List, Dict


class OpenAICompatibleEngine(BaseEngine):
    """OpenAI协议兼容的LLM引擎（支持DeepSeek等）"""

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500
    ):
        """
        初始化LLM引擎

        Args:
            api_base: API基础URL
            api_key: API密钥
            model: 模型名称
            system_prompt: 系统提示词
            temperature: 温度参数
            max_tokens: 最大token数
        """
        self.api_base = api_base
        self.api_key = api_key
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens

        self.client = None
        self.conversation_history: List[Dict[str, str]] = []

    async def initialize(self):
        """初始化OpenAI客户端"""
        try:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.api_base
            )
            logger.info(f"LLM引擎已初始化: {self.model}")
            logger.debug(f"API Base: {self.api_base}")

        except Exception as e:
            logger.error(f"初始化LLM引擎失败: {e}")
            raise

    async def chat_stream(self, message: str) -> AsyncGenerator[str, None]:
        """
        流式对话

        Args:
            message: 用户消息

        Yields:
            生成的token
        """
        if not self.client:
            raise RuntimeError("LLM引擎未初始化")

        # 添加用户消息到历史
        self.conversation_history.append({"role": "user", "content": message})

        # 构造消息
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.conversation_history
        ]

        try:
            # 流式请求
            full_response = ""

            logger.debug(f"发起LLM请求: {message[:50]}...")

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full_response += token
                    yield token

            # 添加助手回复到历史
            self.conversation_history.append({"role": "assistant", "content": full_response})

            logger.info(f"🤖 LLM回复: {full_response}")

        except Exception as e:
            logger.error(f"LLM生成失败: {e}")
            # 生成错误提示
            error_msg = "抱歉，我遇到了一些问题。"
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            yield error_msg

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        logger.debug("对话历史已清空")

    def get_history_length(self) -> int:
        """获取对话历史长度"""
        return len(self.conversation_history)

    async def cleanup(self):
        """清理资源"""
        if self.client:
            await self.client.close()
        self.conversation_history = []
        logger.info("LLM引擎已清理")
