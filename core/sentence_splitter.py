"""句子切分器 - 按标点符号切分LLM生成的句子"""
from loguru import logger
from typing import Optional


class SentenceSplitter:
    """句子切分器 - 将LLM流式输出按句子切分"""

    # 中文句子结束标点
    SENTENCE_ENDINGS = ['。', '！', '?', '？', '；', '…']

    def __init__(self):
        """初始化切分器"""
        self.buffer = ""

    def add_token(self, token: str) -> Optional[str]:
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
                sentence = self.buffer[:idx + 1].strip()
                self.buffer = self.buffer[idx + 1:]

                if sentence:
                    logger.debug(f"📝 切分出句子: {sentence}")
                    return sentence

        # 如果缓冲区过长（超过100字），也返回
        if len(self.buffer) > 100:
            sentence = self.buffer.strip()
            self.buffer = ""
            if sentence:
                logger.debug(f"📝 缓冲区过长，强制切分: {sentence[:30]}...")
                return sentence

        return None

    def flush(self) -> Optional[str]:
        """
        刷新缓冲区，返回剩余内容

        Returns:
            剩余文本或None
        """
        if self.buffer.strip():
            sentence = self.buffer.strip()
            self.buffer = ""
            logger.debug(f"📝 刷新剩余: {sentence}")
            return sentence
        return None

    def reset(self):
        """重置缓冲区"""
        self.buffer = ""
        logger.debug("句子切分器已重置")
