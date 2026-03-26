import base64
import json
import random
import time

from an_contract.framework.agent_entity import AgentResponseAdditional
from an_contract.framework.stream_entity import (
    CesStreamFormat,
    CesStreamType,
    ChatStreamMessage,
)
from an_copilot.framework.ces.gpt_stream import GPTStream


class CesStreamSender:
    def __init__(self, ces_stream: GPTStream):
        self.ces_stream = ces_stream

    def send_msg(
        self,
        session_id: str,
        request_id: str,
        message: str = "",
        begin_time: float = None,
    ):
        """
        持久消息发送流程：begin -> send_start -> send_answer -> send_end -> end

        Args:
            session_id: 会话ID
            request_id: 请求ID
            message: 要发送的消息内容，默认为空字符串
            begin_time: 开始时间，如果为None则使用当前时间
        """
        if begin_time is None:
            begin_time = time.time()

        if self.ces_stream and self.ces_stream.enabled:
            # 完整流程：begin -> send_start -> send_answer -> send_end -> end
            self.begin(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
            )
            self.send_start(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
            )
            self._send_answer(
                session_id=session_id,
                request_id=request_id,
                message=message,
                begin_time=begin_time,
            )
            self.send_end(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
            )
            self.end(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
            )

    def send_attachment(
        self,
        session_id: str,
        request_id: str,
        agent_additional: AgentResponseAdditional,
        begin_time: float = None,
    ):
        if begin_time is None:
            begin_time = time.time()

        if self.ces_stream and self.ces_stream.enabled:
            self._send_additional(
                session_id=session_id,
                request_id=request_id,
                agent_additional=agent_additional,
                begin_time=begin_time,
            )

    def begin(self, session_id: str, request_id: str, begin_time: float):
        if self.ces_stream and self.ces_stream.enabled:
            self.ces_stream.send(
                ChatStreamMessage(
                    type=CesStreamType.multi_agent_start,
                    stream=True,
                    session_id=session_id,
                    request_id=request_id,
                    message="",
                    format=CesStreamFormat.text,
                    duration=int(time.time() - begin_time),
                )
            )

    def end(self, session_id: str, request_id: str, begin_time: float):
        if self.ces_stream and self.ces_stream.enabled:
            self.ces_stream.send(
                ChatStreamMessage(
                    type=CesStreamType.multi_agent_end,
                    stream=True,
                    session_id=session_id,
                    request_id=request_id,
                    message="",
                    format=CesStreamFormat.text,
                    duration=int(time.time() - begin_time),
                )
            )

    def send_start(self, session_id: str, request_id: str, begin_time: float):
        if self.ces_stream and self.ces_stream.enabled:
            self.ces_stream.send(
                ChatStreamMessage(
                    type=CesStreamType.start,
                    stream=True,
                    session_id=session_id,
                    request_id=request_id,
                    message="",
                    format=CesStreamFormat.text,
                    duration=int(time.time() - begin_time),
                )
            )

    def send_end(self, session_id: str, request_id: str, begin_time: float):
        if self.ces_stream and self.ces_stream.enabled:
            self.ces_stream.send(
                ChatStreamMessage(
                    type=CesStreamType.end,
                    stream=True,
                    session_id=session_id,
                    request_id=request_id,
                    message="",
                    format=CesStreamFormat.text,
                    duration=int(time.time() - begin_time),
                )
            )

    def _send_answer(
        self, session_id: str, request_id: str, message: str, begin_time: float
    ):
        if self.ces_stream and self.ces_stream.enabled:
            # 模拟大模型流式输出效果
            self._send_streaming_message(session_id, request_id, message, begin_time)

    def _send_streaming_message(
        self, session_id: str, request_id: str, message: str, begin_time: float
    ):
        """
        模拟大模型流式输出效果，将消息随机分拆成1-5长度不等的字符，
        遍历调用self.ces_stream.send方法，每次调用后增加0.1-0.5s的随机sleep

        Args:
            session_id: 会话ID
            request_id: 请求ID
            message: 要发送的消息内容
            begin_time: 开始时间
        """
        if not message:
            return

        # 将消息随机分拆成3-15个字符的片段
        chunks = []
        i = 0
        while i < len(message):
            chunk_size = random.randint(6, 30)
            # 确保不超过消息长度
            chunk_size = min(chunk_size, len(message) - i)
            chunks.append(message[i:i + chunk_size])
            i += chunk_size

        # 遍历发送每个片段
        for chunk in chunks:
            self.ces_stream.send(
                ChatStreamMessage(
                    type=CesStreamType.answer,
                    stream=True,
                    session_id=session_id,
                    request_id=request_id,
                    message=chunk,
                    format=CesStreamFormat.text,
                    duration=int(time.time() - begin_time),
                )
            )
            # 随机延迟0.1-0.3秒
            sleep_time = random.uniform(0.1, 0.3)
            time.sleep(sleep_time)

    def _send_additional(
        self,
        session_id: str,
        request_id: str,
        agent_additional: AgentResponseAdditional,
        begin_time: float,
    ):
        if self.ces_stream and self.ces_stream.enabled:
            self.ces_stream.send(
                ChatStreamMessage(
                    type=CesStreamType.answer,
                    stream=False,
                    session_id=session_id,
                    request_id=request_id,
                    message=json.dumps(
                        [
                            {
                                "type": agent_additional.type.value,
                                "value": base64.b64encode(
                                    agent_additional.value.encode("utf-8")
                                ).decode("utf-8"),
                            }
                        ],
                        ensure_ascii=False,
                    ),
                    format=CesStreamFormat.additional,
                    role="base64",
                    duration=int(time.time() - begin_time),
                )
            )

    def send_mock_btree_message(
        self,
        session_id: str,
        request_id: str,
        message: str,
        begin_time: float,
    ):
        if self.ces_stream and self.ces_stream.enabled:
            time.sleep(2)
            self.send_start(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
            )
            self._send_answer(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
                message=message,
            )
            self.send_end(
                session_id=session_id,
                request_id=request_id,
                begin_time=begin_time,
            )
            time.sleep(3)

    def send_answer_additional_message(self,
                                       session_id: str,
                                       request_id,
                                       message,
    ):
        self.ces_stream.send_answer_bubble(
            session_id=session_id,
            request_id=request_id,
            additions=[message],
            format=CesStreamFormat.additional,
        )


