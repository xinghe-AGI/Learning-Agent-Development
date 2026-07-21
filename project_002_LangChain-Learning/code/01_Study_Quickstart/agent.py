# 导入操作系统模块，用于设置和读取环境变量
import os
# 从 LangChain 导入 create_agent 方法，用于创建智能体（Agent）
from langchain.agents import create_agent
# 从 LangGraph 导入内存检查点存储器，用于短期记忆与会话状态持久化
from langgraph.checkpoint.memory import InMemorySaver
# 从 LangChain 导入 ToolStrategy，用于指定代理使用“工具调用”的结构化输出格式
from langchain.agents.structured_output import ToolStrategy, ProviderStrategy
# 从自定义配置模块导入 Config 类，用于读取模型类型等配置
from utils.config import Config
# 从自定义 LLM 工具模块导入 get_llm 方法，用于获取对话模型和向量模型实例
from utils.llms import get_llm
# 从自定义工具模块导入 get_tools 方法，用于获取可供 Agent 调用的工具列表
from utils.tools import get_tools
# 从自定义模型定义模块导入上下文 Context 和结构化响应模型 ResponseFormat
from utils.models import Context, WeatherResponseFormat
# 从自定义日志模块导入 LoggerManager，用于获取日志记录器实例
from utils.logger import LoggerManager
# 从自定义工具模块导入 build_response_record 方法，用于获取每次调⽤的模型、输⼊、输出、Token ⽤量和耗时
from utils.call_records import build_response_record
'''
agent.py  创建和运行 Agent，演示多轮对话
包含  
LangSmith                       设置 LangSmith 相关环境变量，用于观测与调试 Agent 执行过程
looger                          获取全局日志记录器，用于输出运行过程中的日志信息
create_agent                    用 LangChain 的 create_agent 创建一个 Agent 实例
    ├──model                        根据配置中指定的 LLM 类型，获取对话模型 llm_chat 实例
    ├──SYSTEM_PROMPT                定义系统提示词，指定 Agent 的角色和行为约束
    ├──tools                        获取当前智能体可用的工具列表
    ├──context_schema               指定上下文对象的 schema，用于扩展运行时上下文信息（如 user_id）
    ├──response_format              使用 ToolStrategy + ResponseFormat 定义结构化输出格式，支持从 Agent 状态中读取 structured_response 字段
    ├──checkpointer                 创建一个基于内存的检查点存储器，用于保存对话状态，实现短期记忆与多轮会话关联


    
'''
# 设置 LangSmith 相关环境变量，开启链路追踪，用于观测与调试 Agent 执行过程
os.environ["LANGSMITH_TRACING"] = "true"
# 从外部环境读取 LangSmith API Key；不存在时不写入 os.environ，避免把 None 当成环境变量值
langsmith_api_key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
if langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = langsmith_api_key

# 获取全局日志记录器，用于输出运行过程中的日志信息
logger = LoggerManager.get_logger()

# 根据配置中指定的 LLM 类型，获取对话模型 llm_chat 和嵌入模型 llm_embedding 实例
llm_chat, llm_embedding = get_llm(Config.LLM_TYPE)

# 获取当前智能体可用的工具列表
tools = get_tools()

# 定义系统提示词，指定 Agent 的角色和行为约束
SYSTEM_PROMPT = """你是一名擅长讲冷笑话的专业天气预报员。

你可以使用两个工具：

get_weather_for_location：用于获取某个具体地点的天气

get_user_location：用于获取用户当前所在位置

如果用户向你询问天气，一定要先确认地点。
如果从问题中可以判断出用户指的是“我所在的地方”的天气，就使用 get_user_location 工具来获取用户的位置。"""

# 创建一个基于内存的检查点存储器，用于保存对话状态，实现短期记忆与多轮会话关联
# 测试开发的时候可以使用在实际生产中是不能进行使用的
checkpointer = InMemorySaver()

# 使用 LangChain 的 create_agent 创建一个 Agent 实例
# - model: 指定使用的对话 LLM 模型
# - system_prompt: 指定系统级提示词，约束 Agent 行为
# - tools: 传入可供 Agent 调用的工具列表
# - context_schema: 指定上下文对象的 schema，用于扩展运行时上下文信息（如 user_id）
# - response_format: 使用 ToolStrategy + ResponseFormat 定义结构化输出格式，支持从 Agent 状态中读取 structured_response 字段
# - checkpointer: 传入 InMemorySaver，使 Agent 具备按线程维度存储和恢复对话状态的能力
agent = create_agent(
    model=llm_chat,
    system_prompt=SYSTEM_PROMPT,
    tools=tools,
    context_schema=Context,
    response_format=WeatherResponseFormat,
    # response_format=ToolStrategy(WeatherResponseFormat),
    # response_format=ProviderStrategy(WeatherResponseFormat,strict=True),
    checkpointer=checkpointer
)

# 定义调用配置，其中 configurable.thread_id 用于标识一段对话的唯一“线程 ID”
# 不同 thread_id 之间状态隔离，相同 thread_id 则共享对话上下文与短期记忆
# 在同一个 Python 进程、同一个 checkpointer 实例中：
# 不同 thread_id 的 messages 状态相互隔离；
# 相同 thread_id 会从 checkpointer 恢复上一轮 messages，实现短期对话状态延续。
config1 = {"configurable": {"thread_id": "1"}}
config2 = {"configurable": {"thread_id": "2"}}
config3 = {"configurable": {"thread_id": "3"}}

# 调用 Agent 进行第一次对话
# - messages: 传入用户消息列表，这里用户问“外面的天气怎么样？”
# - config: 传入包含 thread_id 的配置，用于绑定会话上下文
# - context: 传入自定义的 Context 对象（如包含 user_id 等业务相关信息）

######################      北京      ########################
# 本次询问“天气如何？”
response = agent.invoke(
    {"messages": [{"role": "user", "content": "外面的天气怎么样？记住我的暗号是 banana-007"}]},
    config=config1,
    context=Context(user_id="1")
)
print(response)
print("-----------------------")
print(response["messages"])
# 通过日志记录器输出 Agent 返回的结构化响应部分（structured_response 一般是按 ResponseFormat 定义的结构化数据），便于排查与分析
logger.info(f"北京Agent首次回复是: {response['structured_response']}")
logger.info(f"北京Agent首次调用记录是: {build_response_record(response)}")

# 再次调用 Agent，继续同一 thread_id 下的对话，从而复用短期记忆和已有上下文
# 本次询问“我现在在哪里？”
response = agent.invoke(
    {"messages": [{"role": "user", "content": "我现在在哪里？暗号是什么？"}]},
    config=config1,
    context=Context(user_id="1")
)
# 通过日志记录器记录第二轮对话的 structured_response 结果
logger.info(f"北京Agent第二次回复是: : {response['structured_response']}")
logger.info(f"北京Agent第二次调用记录是: {build_response_record(response)}")
#
# ######################      上海     ########################
# response = agent.invoke(
#     {"messages": [{"role": "user", "content": "外面的天气怎么样？"}]},
#     config=config2,
#     context=Context(user_id="2")
# )
# logger.info(f"上海Agent首次回复是: {response['structured_response']}")
#
# # 本次询问"我上一个问题是什么？我现在在哪里？"，查看在同一 thread_id 下是否能复用短期记忆和已有上下文
# response = agent.invoke(
#     {"messages": [{"role": "user", "content": "我上一个问题是什么？我现在在哪里？"}]},
#     config=config2,
#     context=Context(user_id="2")
# )
# # 通过日志记录器记录第二轮对话的结构化响应内容
# logger.info(f"上海Agent第二次回复是: : {response['structured_response']}")
#
######################      深圳      ########################
# 明确询问"我现在在哪里？"，Agent 可以结合前文与工具调用进行回答
response = agent.invoke(
    {"messages": [{"role": "user", "content": "我上一个问题是什么？我现在在哪里？暗号是什么？"}]},
    config=config3,
    context=Context(user_id="3")
)
logger.info(f"深圳Agent首次回复是: : {response['structured_response']}")
logger.info(f"深圳Agent首次调用记录是: {build_response_record(response)}")

print("已结束全部输出！")
