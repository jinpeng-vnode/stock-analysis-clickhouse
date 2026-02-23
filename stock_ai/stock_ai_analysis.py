#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
基于 DeepSeek 函数调用的股票自动分析脚本
使用多维度数据读取器进行数据获取
"""

from openai import OpenAI
import sys
import os
import json
import time
from typing import Dict, List, Optional, Any

# 添加当前目录到路径，以便导入 readers
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# 导入数据读取器和函数定义
from readers.search_stocks_reader import search_stocks, function_define as search_stocks_function
from readers.stock_info_reader import get_stock_info, function_define as stock_info_function
from readers.money_flow_reader import read_money_flow, function_define as money_flow_function
from readers.news_reader import read_news, function_define as news_function
from readers.announcement_reader import read_announcement, function_define as announcement_function
from readers.company_info_reader import read_company_info, function_define as company_info_function
from readers.financial_reader import read_financial, function_define as financial_function
from readers.kline_reader import read_kline, function_define as kline_function

# DeepSeek API 配置
API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
# 模型选择：
# - deepseek-chat: 支持函数调用和流式输出，但不显示思考过程
# - deepseek-reasoner: 显示思考过程，但如果传入tools参数会自动切换到deepseek-chat
# 注意：由于需要函数调用功能，建议使用 deepseek-chat
MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# ========== 定义工具列表（供DeepSeek使用） ==========

# 合并所有工具定义
TOOLS = [
    search_stocks_function,
    stock_info_function,
    money_flow_function,
    news_function,
    announcement_function,
    company_info_function,
    financial_function,
    kline_function,
]


# ========== 主函数 ==========

def execute_function_call(function_name: str, arguments: Dict) -> str:
    """执行函数调用并返回结果"""
    # 从当前模块的全局命名空间查找函数
    func = globals().get(function_name)
    if func is None or not callable(func):
        return json.dumps({"error": f"未知函数: {function_name}"}, ensure_ascii=False)

    try:
        result = func(**arguments)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": f"函数执行错误: {str(e)}"}, ensure_ascii=False)


def chat_with_deepseek(client, messages, model=None, stream=True):
    """
    与DeepSeek对话，支持函数调用
    
    Args:
        client: OpenAI客户端实例
        messages: 对话消息列表
        model: 模型名称，如果为None则使用全局MODEL配置
        stream: 是否使用流式输出
    """
    # 使用全局MODEL配置如果未指定
    if model is None:
        model = MODEL

    max_iterations = 10  # 最大迭代次数，防止无限循环
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        print(f"\n[迭代 {iteration}/{max_iterations}] 正在调用DeepSeek API (模型: {model})...")

        try:
            # 调用API（设置超时时间）
            print(f"   发送消息: {len(messages)} 条")

            if stream:
                # 流式输出模式（用于显示思考过程）
                print(f"   使用流式输出模式...")
                response_text = ""
                reasoning_text = ""
                tool_calls_list = []

                stream_response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=True,
                    temperature=0.7,
                    timeout=60
                )

                print(f"\n💭 思考过程: ", end="", flush=True)
                for chunk in stream_response:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta

                        # 处理思考过程
                        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                            reasoning_text += delta.reasoning_content
                            print(delta.reasoning_content, end="", flush=True)

                        # 处理普通内容
                        if hasattr(delta, 'content') and delta.content:
                            response_text += delta.content

                        # 处理函数调用
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tool_call_delta in delta.tool_calls:
                                idx = tool_call_delta.index
                                if idx >= len(tool_calls_list):
                                    tool_calls_list.append({
                                        "id": tool_call_delta.id if hasattr(tool_call_delta, 'id') else "",
                                        "type": "function",
                                        "function": {
                                            "name": "",
                                            "arguments": ""
                                        }
                                    })

                                if hasattr(tool_call_delta, 'function'):
                                    if tool_call_delta.function.name:
                                        tool_calls_list[idx]["function"]["name"] = tool_call_delta.function.name
                                    if tool_call_delta.function.arguments:
                                        tool_calls_list[idx]["function"][
                                            "arguments"] += tool_call_delta.function.arguments

                print("\n")  # 思考过程结束，换行

                # 构建message对象（支持流式函数调用）
                if tool_calls_list:
                    # 有函数调用，构建tool_calls对象
                    class ToolCall:
                        def __init__(self, data):
                            self.id = data["id"]
                            self.type = data["type"]
                            self.function = type('Function', (), {
                                'name': data["function"]["name"],
                                'arguments': data["function"]["arguments"]
                            })()

                    message = type('Message', (), {
                        'content': response_text if response_text else None,
                        'reasoning_content': reasoning_text if reasoning_text else None,
                        'tool_calls': [ToolCall(tc) for tc in tool_calls_list]
                    })()
                else:
                    # 没有函数调用
                    message = type('Message', (), {
                        'content': response_text,
                        'reasoning_content': reasoning_text if reasoning_text else None,
                        'tool_calls': None
                    })()
            else:
                # 非流式输出模式（函数调用必需）
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=False,
                    temperature=0.7,
                    timeout=60
                )

                print(f"   API响应成功")
                message = response.choices[0].message

            # 检查是否有思考过程（reasoning_content）
            if hasattr(message, 'reasoning_content') and message.reasoning_content:
                print(f"\n💭 思考过程:\n{message.reasoning_content}\n")

            # 检查是否有函数调用
            print(f"   检查是否有函数调用...")
            if message.tool_calls:
                # 处理函数调用
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    print(f"\n🔧 调用函数: {function_name}")
                    print(f"   参数: {json.dumps(function_args, ensure_ascii=False)}")

                    # 执行函数
                    function_result = execute_function_call(function_name, function_args)

                    print(f"   结果: {function_result[:200]}..." if len(
                        function_result) > 200 else f"   结果: {function_result}")

                    # 将函数调用和结果添加到消息历史
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })

                    # 添加函数执行结果
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": function_result
                    })

                # 继续对话，让AI基于函数结果生成回复
                continue

            # 没有函数调用，返回最终回复
            content = message.content
            if content:
                # 如果有思考过程，先显示思考过程
                if hasattr(message, 'reasoning_content') and message.reasoning_content:
                    print(f"\n💭 思考过程:\n{message.reasoning_content}\n")
                print(f"\n🤖 DeepSeek: {content}\n")
                return content
            else:
                print("\n🤖 DeepSeek: (无回复内容)\n")
                return ""

        except Exception as e:
            print(f"\n❌ 错误: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return None

    print("\n⚠️  达到最大迭代次数，可能存在问题\n")
    return None


def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print("🤖 DeepSeek 股票自动分析工具")
    print("=" * 60)
    print("\n功能说明：")
    print("  - 支持搜索股票（代码或名称）")
    print("  - 支持多维度数据读取：日K线、资金流向、资讯、公告、公司资料、财务")
    print("  - AI会自动调用相关函数获取数据并进行分析")
    print("\n示例问题：")
    print("  - '帮我搜索一下平安银行'")
    print("  - '分析一下000001这只股票的多维度数据'")
    print("  - '获取600519的资金流向和财务数据'")
    print("  - '分析贵州茅台的资讯、公告情况'")
    print("\n输入 'quit' 或 'exit' 退出程序")
    print("输入 'clear' 清空对话历史")
    print("=" * 60)
    print()


def main():
    """主函数"""
    # 初始化客户端（设置超时时间）
    client = OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=60.0  # 设置60秒超时
    )

    # 打印欢迎信息
    print_welcome()

    # 对话历史
    messages = []

    # 添加系统提示
    messages.append({
        "role": "system",
        "content": """你是一个专业的股票分析助手。你可以通过调用函数来获取股票的多维度数据并进行分析。

你可以获取以下6个维度的数据（数据通过本地API获取）：
1. 日K线数据（read_kline）：开盘价、收盘价、最高价、最低价、成交量、涨跌幅等
2. 资金流向数据（read_money_flow）：主力净流入、各类型资金流向、多日累计净流入
3. 资讯数据（read_news）：新闻列表、发布时间、来源、内容摘要（使用秘塔AI）
4. 公告数据（read_announcement）：公告类型、标题、发布时间、内容摘要
5. 公司资料数据（read_company_info）：基本信息、行业、市场、成立时间等
6. 财务数据（read_financial）：盈利能力、偿债能力、成长性指标

当用户询问股票相关信息时，你应该：
1. 如果用户提到股票名称或代码，先搜索或获取股票信息
2. 根据用户需求调用相应的数据读取函数获取各维度数据
3. 基于获取的多维度原始数据进行综合分析，给出专业的投资建议
"""
    })

    # 交互式对话循环
    print("\n" + "=" * 60)
    print("💬 开始对话（输入 'quit' 或 'exit' 退出，'clear' 清空历史）")
    print("=" * 60)
    print()

    while True:
        try:
            # 获取用户输入
            user_input = input("您: ").strip()

            # 处理退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见！")
                break

            # 处理清空历史命令
            if user_input.lower() in ['clear', 'reset']:
                messages = [messages[0]]  # 保留系统提示
                print("✅ 对话历史已清空\n")
                continue

            # 跳过空输入
            if not user_input:
                continue

            # 添加用户消息到历史
            messages.append({
                "role": "user",
                "content": user_input
            })

            # 调用DeepSeek API（支持函数调用）
            response_content = chat_with_deepseek(client, messages)

            # 添加助手回复到历史
            if response_content:
                messages.append({
                    "role": "assistant",
                    "content": response_content
                })

            print()  # 空行分隔

        except KeyboardInterrupt:
            print("\n\n👋 再见！")
            break
        except Exception as e:
            print(f"\n❌ 发生错误: {str(e)}\n")
            import traceback
            traceback.print_exc()
            continue


if __name__ == "__main__":
    main()
