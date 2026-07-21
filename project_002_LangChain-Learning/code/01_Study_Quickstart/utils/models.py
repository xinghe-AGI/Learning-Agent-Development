# 从 dataclasses 模块导入 dataclass 装饰器，用于简化数据类的定义
from dataclasses import dataclass

'''
    models.py  定义LLM的Context和ResponseFormat
    包含  
    Context                 定义运行时上下文数据模型，用于在 Agent/工具执行时传递用户相关信息
    ResponseFormat          定义 Agent 以下面的结构去响应数据结果
        punny_response          用于存放包含谐音梗 / 冷笑话的主要回复内容
        weather_location        用于存放地址信息
        weather_conditions      用于补充与天气相关的有趣信息
'''
# 使用 @dataclass 定义运行时上下文数据模型，用于在 Agent/工具执行时传递用户相关信息
@dataclass
class Context:
    # 表示用户唯一标识，用于在会话、工具调用等场景中区分不同用户
    user_id: str

# 使用 @dataclass 定义 Agent 的结构化响应数据模型
@dataclass
class WeatherResponseFormat:
    # punny_response 为必填字段，用于存放包含谐音梗 / 冷笑话的主要回复内容
    # 该字段通常会由 LLM 根据系统提示词和用户问题生成
    punny_response: str
    # weather_location 为必填字段，用于存放地址信息
    # 该字段通常会由 LLM 根据系统提示词和用户问题生成
    weather_location: str
    # weather_conditions 为可选字段，用于补充与天气相关的有趣信息
    # 类型注解为 str | None，表示可以是字符串或 None
    weather_conditions: str | None = None



