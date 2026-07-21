from dataclasses import dataclass
import importlib
import importlib.util
from pathlib import Path
import sys

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _load_call_records_module():
    spec = importlib.util.find_spec("utils.call_records")
    assert spec is not None, "utils/call_records.py 应当存在"
    return importlib.import_module("utils.call_records")


@dataclass
class DemoResponse:
    answer: str
    city: str


def test_build_response_record_sums_usage_and_provider_latency():
    call_records = _load_call_records_module()

    first_call = AIMessage(
        content="",
        id="ai-1",
        usage_metadata={
            "input_tokens": 10,
            "output_tokens": 2,
            "total_tokens": 12,
        },
        response_metadata={
            "model_provider": "openai",
            "model_name": "qwen3.7-plus",
            "finish_reason": "tool_calls",
            "latency_checkpoint": {"total_duration_ms": 120},
        },
        tool_calls=[
            {
                "name": "get_user_location",
                "args": {},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )
    second_call = AIMessage(
        content="",
        id="ai-2",
        usage_metadata={
            "input_tokens": 20,
            "output_tokens": 5,
            "total_tokens": 25,
        },
        response_metadata={
            "model_provider": "openai",
            "model_name": "qwen3.7-plus",
            "finish_reason": "tool_calls",
            "latency_checkpoint": {"total_duration_ms": 230},
            # 标准化 usage 存在时，不应再重复累计 Provider 原始 usage。
            "token_usage": {
                "prompt_tokens": 999,
                "completion_tokens": 999,
                "total_tokens": 1998,
            },
        },
        tool_calls=[
            {
                "name": "DemoResponse",
                "args": {"answer": "晴天", "city": "北京"},
                "id": "call-2",
                "type": "tool_call",
            }
        ],
    )

    response = {
        "messages": [
            HumanMessage(content="北京天气怎么样？"),
            first_call,
            ToolMessage(content="北京", tool_call_id="call-1"),
            second_call,
        ],
        "structured_response": DemoResponse(answer="晴天", city="北京"),
    }

    record = call_records.build_response_record(response)

    assert record == {
        "model": "qwen3.7-plus",
        "provider": "openai",
        "input": {
            "messages": [
                {"role": "user", "content": "北京天气怎么样？"},
            ]
        },
        "output": {"answer": "晴天", "city": "北京"},
        "usage": {
            "inputTokens": 30,
            "outputTokens": 7,
            "totalTokens": 37,
        },
        "latencyMs": 350,
    }


def test_build_response_record_falls_back_to_provider_token_usage():
    call_records = _load_call_records_module()

    response = {
        "messages": [
            HumanMessage(content="你好"),
            AIMessage(
                content="你好！",
                response_metadata={
                    "model_provider": "openai",
                    "model_name": "legacy-model",
                    "finish_reason": "stop",
                    "token_usage": {
                        "prompt_tokens": 8,
                        "completion_tokens": 4,
                        "total_tokens": 12,
                    },
                },
            ),
        ],
        "structured_response": {"answer": "你好！"},
    }

    record = call_records.build_response_record(response)

    assert record["usage"] == {
        "inputTokens": 8,
        "outputTokens": 4,
        "totalTokens": 12,
    }
    assert record["latencyMs"] is None


def test_build_response_record_can_include_per_call_details():
    call_records = _load_call_records_module()

    response = {
        "messages": [
            HumanMessage(content="查询天气", id="human-1"),
            AIMessage(
                content="",
                id="ai-1",
                usage_metadata={
                    "input_tokens": 6,
                    "output_tokens": 2,
                    "total_tokens": 8,
                },
                response_metadata={
                    "model_provider": "openai",
                    "model_name": "demo-model",
                    "finish_reason": "tool_calls",
                    "latency_checkpoint": {"total_duration_ms": 80},
                },
                tool_calls=[
                    {
                        "name": "get_weather",
                        "args": {"city": "北京"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(
                content="晴天",
                id="tool-1",
                name="get_weather",
                tool_call_id="call-1",
            ),
        ],
        "structured_response": {"answer": "晴天"},
    }

    record = call_records.build_response_record(
        response,
        include_details=True,
    )

    assert record["llmCallCount"] == 1
    assert record["llmCalls"] == [
        {
            "messageId": "ai-1",
            "modelProvider": "openai",
            "modelName": "demo-model",
            "finishReason": "tool_calls",
            "inputTokens": 6,
            "outputTokens": 2,
            "totalTokens": 8,
            "latencyCheckpoint": {"total_duration_ms": 80},
            "toolCalls": [
                {
                    "name": "get_weather",
                    "args": {"city": "北京"},
                    "id": "call-1",
                    "type": "tool_call",
                }
            ],
        }
    ]
    assert [item["type"] for item in record["messageTrace"]] == [
        "HumanMessage",
        "AIMessage",
        "ToolMessage",
    ]
    assert record["messageTrace"][2]["toolCallId"] == "call-1"
