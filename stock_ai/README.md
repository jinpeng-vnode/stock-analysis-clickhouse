# 股票AI自动分析工具

## 简介

`stock_ai_analysis.py` 是一个基于 DeepSeek API 的智能股票分析脚本。它通过函数调用（Function Calling）机制，让 AI 自动调用多个数据读取器来获取股票的多维度数据，并进行智能分析和回答。

## 核心功能
嗯
### 1. 股票搜索
- 支持按股票代码或名称进行模糊搜索
- 返回匹配的股票列表及其基本信息

### 2. 多维度数据获取
脚本集成了以下 8 个数据读取器，提供全方位的股票数据分析：

- **股票搜索** (`search_stocks`): 根据关键词搜索股票
- **股票信息** (`get_stock_info`): 获取股票基本信息（代码、名称、市场、状态）
- **资金流向** (`read_money_flow`): 获取主力净流入、超大单、大单、中单、小单净流入，以及多日累计净流入统计
- **资讯数据** (`read_news`): 获取股票相关的新闻列表、发布时间、来源、内容摘要
- **公告数据** (`read_announcement`): 获取公告类型、标题、发布时间、内容摘要
- **公司资料** (`read_company_info`): 获取公司基本信息、行业、市场、成立时间等
- **财务数据** (`read_financial`): 获取盈利能力指标（ROE、ROA、净利润率、毛利率）、偿债能力指标（资产负债率、流动比率、速动比率）、成长性指标（营收增长率、净利润增长率、总资产增长率）
- **板块数据** (`read_secto`): 获取板块名称、涨跌幅、板块内排名、板块内其他股票表现

### 3. 智能分析
- AI 会根据用户的问题自动判断需要调用哪些数据读取器
- 对获取的多维度数据进行综合分析
- 提供专业的投资建议和风险提示

## 工作原理

1. **函数调用机制**: 脚本使用 DeepSeek API 的函数调用功能，将 8 个数据读取器作为工具函数注册给 AI
2. **自动决策**: AI 根据用户问题自动决定需要调用哪些函数来获取数据
3. **迭代对话**: 支持多轮函数调用，AI 可以基于前一轮的结果继续调用其他函数，最多迭代 10 次
4. **数据整合**: AI 将获取的多个维度数据进行整合分析，生成综合性的回答

## 使用方法

### 环境配置

1. 设置 DeepSeek API Key（可选，有默认值）:
```bash
export DEEPSEEK_API_KEY="your-api-key"
```

2. 设置 DeepSeek Base URL（可选，默认使用官方地址）:
```bash
export DEEPSEEK_BASE_URL="https://api.deepseek.com/v1"
```

### 运行脚本

```bash
python stock_ai_analysis.py
```

### 示例问题

脚本内置了以下测试问题，会自动执行：

1. "帮我搜索一下平安银行"
2. "分析一下000001这只股票的多维度数据"
3. "获取600519的资金流向和财务数据"
4. "分析贵州茅台的资讯、公告和板块情况"

## 代码结构

```
stock_ai/
├── stock_ai_analysis.py    # 主脚本文件
├── readers/                 # 数据读取器目录
│   ├── search_stocks_reader.py      # 股票搜索读取器
│   ├── stock_info_reader.py         # 股票信息读取器
│   ├── money_flow_reader.py         # 资金流向读取器
│   ├── news_reader.py               # 资讯数据读取器
│   ├── announcement_reader.py       # 公告数据读取器
│   ├── company_info_reader.py       # 公司资料读取器
│   ├── financial_reader.py          # 财务数据读取器
│   └── sector_reader.py             # 板块数据读取器
└── README.md                 # 本文档
```

## 主要函数说明

### `execute_function_call(function_name, arguments)`
执行函数调用并返回结果。从全局命名空间查找对应的函数并执行。

### `chat_with_deepseek(client, messages, model, stream)`
与 DeepSeek API 进行对话，支持函数调用。处理函数调用的迭代逻辑，最多迭代 10 次。

### `main()`
主函数，初始化客户端，执行测试问题列表。

## 注意事项

1. **模拟数据**: 当前版本使用的是模拟数据，不连接真实数据库
2. **API 限制**: 注意 DeepSeek API 的调用频率限制
3. **投资风险**: AI 提供的分析和建议仅供参考，投资有风险，决策需谨慎
4. **迭代限制**: 为防止无限循环，函数调用最多迭代 10 次

## 扩展开发

要添加新的数据读取器：

1. 在 `readers/` 目录下创建新的读取器文件
2. 实现读取函数和 `function_define` 字典
3. 在主脚本中导入并添加到 `TOOLS` 列表
4. 在主脚本中导入函数供 `execute_function_call` 调用

## 技术栈

- Python 3.x
- OpenAI SDK (兼容 DeepSeek API)
- DeepSeek Chat API
- 函数调用（Function Calling）机制

## 许可证

本项目仅供学习和研究使用。

