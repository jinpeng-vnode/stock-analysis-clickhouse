#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调用本地 Ollama deepseek-r1:8b 模型的交互式脚本
支持函数调用功能测试
"""

import ollama
import sys
import json
from datetime import datetime
from typing import List, Dict, Optional


# 模型配置
MODEL_NAME = "deepseek-r1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"


# ========== 定义获取日期的函数 ==========

def get_current_date(format_type: str = "full") -> Dict:
    """
    获取当前日期和时间
    
    Args:
        format_type: 日期格式类型，可选值：
            - "full": 完整日期时间（默认）
            - "date": 仅日期
            - "time": 仅时间
            - "iso": ISO格式
            - "timestamp": 时间戳
    
    Returns:
        包含日期信息的字典
    """
    now = datetime.now()
    
    if format_type == "full":
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": now.strftime("%A"),
            "weekday_cn": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        }
    elif format_type == "date":
        return {
            "date": now.strftime("%Y-%m-%d"),
            "weekday": now.strftime("%A"),
            "weekday_cn": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()]
        }
    elif format_type == "time":
        return {
            "time": now.strftime("%H:%M:%S")
        }
    elif format_type == "iso":
        return {
            "iso": now.isoformat()
        }
    elif format_type == "timestamp":
        return {
            "timestamp": int(now.timestamp()),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        return {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S")
        }


# 函数定义（供模型使用）
get_current_date_function = {
    "type": "function",
    "function": {
        "name": "get_current_date",
        "description": "获取当前日期和时间信息。可以根据不同的格式类型返回日期、时间或时间戳。",
        "parameters": {
            "type": "object",
            "properties": {
                "format_type": {
                    "type": "string",
                    "description": "日期格式类型。可选值：'full'（完整日期时间，默认）、'date'（仅日期）、'time'（仅时间）、'iso'（ISO格式）、'timestamp'（时间戳）",
                    "enum": ["full", "date", "time", "iso", "timestamp"]
                }
            },
            "required": []
        }
    }
}

# 工具列表
TOOLS = [get_current_date_function]


def execute_function_call(function_name: str, arguments: Dict) -> str:
    """
    执行函数调用并返回结果
    
    Args:
        function_name: 函数名称
        arguments: 函数参数
    
    Returns:
        函数执行结果的JSON字符串
    """
    # 从当前模块的全局命名空间查找函数
    func = globals().get(function_name)
    if func is None or not callable(func):
        return json.dumps({"error": f"未知函数: {function_name}"}, ensure_ascii=False)
    
    result = func(**arguments)
    return json.dumps(result, ensure_ascii=False, indent=2)


def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print("🤖 Ollama DeepSeek-R1:8B 对话工具（支持函数调用）")
    print("=" * 60)
    print(f"\n使用模型: {MODEL_NAME}")
    print(f"Ollama 地址: {OLLAMA_BASE_URL}")
    print("\n可用函数:")
    print("  - get_current_date: 获取当前日期和时间")
    print("\n示例问题:")
    print("  - '今天几号？'")
    print("  - '现在是什么时间？'")
    print("  - '获取当前时间戳'")
    print("\n输入 'quit' 或 'exit' 退出程序")
    print("输入 'clear' 清空对话历史")
    print("=" * 60)
    print()


def chat_with_ollama(messages: List[Dict], stream: bool = True) -> Optional[str]:
    """
    与 Ollama 模型对话，支持函数调用
    
    Args:
        messages: 对话消息列表
        stream: 是否使用流式输出
    
    Returns:
        模型回复内容，如果有函数调用则返回None并继续处理
    """
    max_iterations = 10  # 最大迭代次数，防止无限循环
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n[迭代 {iteration}/{max_iterations}] 正在调用 Ollama API...")
        
        try:
            # 对于函数调用，使用非流式模式更可靠
            # 先使用非流式模式检测是否有函数调用
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                tools=TOOLS,
                stream=False
            )
            
            response_text = ""
            tool_calls_list = []
            
            if response.get('message'):
                msg = response['message']
                response_text = msg.get('content', '')
                tool_calls_list = msg.get('tool_calls', [])
            
            # 如果有函数调用，不显示流式输出
            # 如果没有函数调用且需要流式输出，重新用流式模式获取（仅用于显示）
            if not tool_calls_list and stream:
                # 没有函数调用，用流式模式重新获取以显示流式效果
                print("\n🤖 回复: ", end="", flush=True)
                stream_response = ollama.chat(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=TOOLS,
                    stream=True
                )
                
                response_text = ""
                for chunk in stream_response:
                    if chunk.get('message') and chunk['message'].get('content'):
                        content = chunk['message']['content']
                        response_text += content
                        print(content, end="", flush=True)
                    elif chunk.get('content'):
                        content = chunk['content']
                        response_text += content
                        print(content, end="", flush=True)
                print("\n")  # 换行
            
            # 检查是否有函数调用
            if tool_calls_list:
                # 将助手消息（包含函数调用）添加到历史
                messages.append({
                    "role": "assistant",
                    "content": response_text if response_text else None,
                    "tool_calls": tool_calls_list
                })
                
                # 处理每个函数调用
                for tool_call in tool_calls_list:
                    function_name = tool_call.get('function', {}).get('name', '')
                    function_args_str = tool_call.get('function', {}).get('arguments', '{}')
                    
                    # 解析参数
                    try:
                        function_args = json.loads(function_args_str) if isinstance(function_args_str, str) else function_args_str
                    except:
                        function_args = {}
                    
                    print(f"\n🔧 调用函数: {function_name}")
                    print(f"   参数: {json.dumps(function_args, ensure_ascii=False)}")
                    
                    # 执行函数
                    function_result = execute_function_call(function_name, function_args)
                    
                    print(f"   结果: {function_result[:200]}..." if len(function_result) > 200 else f"   结果: {function_result}")
                    
                    # 添加函数执行结果到消息历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get('id', ''),
                        "content": function_result
                    })
                
                # 继续对话，让AI基于函数结果生成回复
                continue
            
            # 没有函数调用，返回最终回复
            if response_text:
                print(f"\n🤖 回复: {response_text}\n")
                return response_text
            else:
                print("\n🤖 回复: (无回复内容)\n")
                return ""
                
        except Exception as e:
            print(f"\n❌ 错误: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return None
    
    print("\n⚠️  达到最大迭代次数，可能存在问题\n")
    return None


def main():
    """主函数"""
    # 打印欢迎信息
    print_welcome()
    
    # 对话历史
    messages = []
    
    # 添加系统提示
    messages.append({
        "role": "system",
        "content": """你是一个有用的AI助手。请用中文回答用户的问题。

你可以调用以下函数来获取信息：
- get_current_date: 获取当前日期和时间信息。当用户询问日期、时间相关问题时，你应该调用这个函数。

请根据用户的问题，决定是否需要调用函数。如果需要，请调用相应的函数获取信息后再回答用户的问题。"""
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
                messages = [messages[0]] if messages and messages[0].get('role') == 'system' else []
                # 如果没有系统消息，添加一个
                if not messages:
                    messages.append({
                        "role": "system",
                        "content": "你是一个有用的AI助手。请用中文回答用户的问题。"
                    })
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
            
            # 调用 Ollama API
            response_content = chat_with_ollama(messages, stream=True)
            
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

