# 📚 arXiv Paper Crawler

一个用于搜索、保存和**AI智能分析** arXiv 论文的 Python Web 应用程序。集成 DeepSeek API 实现论文摘要分析、全文深度分析和多轮问答功能。

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![DeepSeek](https://img.shields.io/badge/DeepSeek-Reasoner-purple.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## ✨ Features

### 📄 论文管理
- 🔍 **智能搜索**: 按关键词、作者或分类搜索论文
- 💾 **本地保存**: 将论文摘要以 JSON 格式存储到本地
- 📥 **PDF下载**: 下载论文 PDF 并自动提取文本内容
- 🌐 **Web界面**: 美观、响应式的 Web 用户界面

### 🤖 AI 智能分析（DeepSeek）
- 📝 **摘要分析**: 使用 DeepSeek 对论文摘要进行深度分析
- 📚 **全文分析**: 对论文全文进行详细分析，生成 HTML 报告
- 💬 **智能问答**: 基于论文内容进行多轮对话，支持上下文记忆
- 🧠 **推理过程**: 展示 AI 的思考和推理过程（Reasoning）
- 📊 **流式输出**: 实时显示 AI 生成内容

### 🛠️ 技术特性
- 📊 **RESTful API**: 完整的 API 接口，支持程序化集成
- ⚡ **异步架构**: 基于 async Python 构建，高效处理请求
- 📱 **响应式设计**: 支持各种设备访问
- 🔒 **HTTP认证**: 可选的 HTTP Basic Auth 保护

## 🚀 Quick Start

### Prerequisites

- Python 3.12 或更高版本
- pip (Python 包管理器)
- DeepSeek API Key（用于 AI 分析功能）

### Installation

1. **克隆/进入项目目录**

```bash
cd /path/to/python_web_crawler
```

2. **创建虚拟环境（推荐）**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装依赖**

```bash
pip install -r requirements.txt
```

4. **配置环境变量**

创建 `.env` 文件（或设置环境变量）：

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
vim .env
```

`.env` 文件示例：

```env
# DeepSeek API 配置（必需，用于AI分析功能）
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here

# 可选配置
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True

# 认证配置（可选）
AUTH_ENABLED=True
AUTH_USERNAME=admin
AUTH_PASSWORD=your_secure_password
```

5. **运行应用**

```bash
python run.py
```

6. **访问应用**

打开浏览器访问 [http://localhost:8000](http://localhost:8000)

## 🤖 DeepSeek API 配置

### 获取 API Key

1. 访问 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册并登录账号
3. 在控制台创建 API Key
4. 将 API Key 配置到环境变量 `DEEPSEEK_API_KEY`

### 配置选项

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | `""` | **必需** - DeepSeek API 密钥 |
| `DEEPSEEK_API_BASE_URL` | `https://api.deepseek.com` | API 基础 URL |
| `DEEPSEEK_MODEL` | `deepseek-reasoner` | 使用的模型（支持推理过程展示） |
| `DEEPSEEK_MAX_TOKENS` | `65536` | 最大 token 数量 |

### 支持的模型

- **`deepseek-reasoner`**（推荐）: 支持展示推理过程，适合学术分析
- **`deepseek-chat`**: 标准对话模型

### API 使用说明

本应用使用 OpenAI SDK 兼容的方式调用 DeepSeek API：

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-deepseek-api-key",
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[
        {"role": "system", "content": "你是一位学术论文分析专家"},
        {"role": "user", "content": "分析这篇论文..."}
    ],
    stream=True
)
```

### AI 功能使用

#### 1. 摘要分析

在论文详情页，输入分析提示词（如"总结主要贡献"、"分析方法论"），点击"Analyze Abstract"即可获得 AI 分析报告。

#### 2. 全文分析

1. 首先点击 "Download PDF & Extract Text" 下载并提取论文文本
2. 在"Fulltext Analysis"部分输入分析提示词
3. 点击 "Analyze Fulltext" 进行全文深度分析

#### 3. 智能问答（Q&A）

1. 确保已下载并提取论文文本
2. 在 "Q&A with DeepSeek" 部分输入问题
3. 支持多轮对话，AI 会记住上下文
4. 问答历史会自动保存

## 📁 Project Structure

```
python_web_crawler/
├── app/                          # Web 应用模块
│   ├── __init__.py
│   ├── main.py                   # FastAPI 应用入口
│   ├── auth.py                   # HTTP Basic Auth
│   ├── routes/                   # API 路由
│   │   ├── search.py             # 搜索端点
│   │   ├── papers.py             # 论文管理端点
│   │   └── analysis.py           # AI 分析端点
│   ├── templates/                # Jinja2 HTML 模板
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── results.html
│   │   ├── papers.html
│   │   └── paper_detail.html
│   └── static/                   # 静态资源
│       ├── css/style.css
│       ├── js/app.js
│       └── vendor/               # 本地化的第三方库
│           ├── katex/            # 数学公式渲染
│           ├── marked/           # Markdown 渲染
│           └── highlight/        # 代码高亮
│
├── crawler/                      # 爬虫和 AI 模块
│   ├── __init__.py
│   ├── models.py                 # 数据模型
│   ├── arxiv_client.py           # arXiv API 客户端
│   └── deepseek_client.py        # DeepSeek API 客户端
│
├── storage/                      # 存储模块
│   ├── __init__.py
│   └── file_handler.py           # 文件操作
│
├── config/                       # 配置模块
│   ├── __init__.py
│   └── settings.py               # 应用配置
│
├── data/                         # 数据存储目录
│   ├── papers/                   # 论文 JSON 数据
│   ├── pdfs/                     # 下载的 PDF 文件
│   ├── texts/                    # 提取的文本内容
│   ├── analysis/                 # AI 分析报告（HTML）
│   └── qa/                       # 问答历史记录
│
├── requirements.txt              # Python 依赖
├── run.py                        # 应用启动入口
└── README.md                     # 项目说明
```

## 🔧 Configuration

所有配置可通过环境变量或 `.env` 文件设置：

### 应用配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_HOST` | `0.0.0.0` | 服务器主机 |
| `APP_PORT` | `8000` | 服务器端口 |
| `DEBUG` | `True` | 调试模式 |

### 认证配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AUTH_ENABLED` | `True` | 是否启用 HTTP Basic Auth |
| `AUTH_USERNAME` | `admin` | 认证用户名 |
| `AUTH_PASSWORD` | `change_me_to_secure_password` | 认证密码（请修改！） |

### arXiv API 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ARXIV_MAX_RESULTS` | `10` | 默认搜索结果数量 |
| `ARXIV_RATE_LIMIT_DELAY` | `3.0` | API 请求间隔（秒） |

### DeepSeek API 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | `""` | **必需** - API 密钥 |
| `DEEPSEEK_API_BASE_URL` | `https://api.deepseek.com` | API 基础 URL |
| `DEEPSEEK_MODEL` | `deepseek-reasoner` | 使用的模型 |
| `DEEPSEEK_MAX_TOKENS` | `65536` | 最大 token 数 |

## 📖 API Documentation

服务器运行后，访问：

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 主要 API 端点

#### 搜索相关

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/` | 首页 |
| `POST` | `/search` | 搜索论文（表单） |
| `GET` | `/search?q=...` | 搜索论文（URL参数） |
| `GET` | `/api/search` | 搜索 API（JSON） |
| `GET` | `/api/search/author` | 按作者搜索 |
| `GET` | `/api/search/category` | 按分类搜索 |

#### 论文管理

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/papers` | 已保存论文列表 |
| `GET` | `/papers/{id}` | 论文详情页 |
| `POST` | `/papers/api/save/{id}` | 保存论文 |
| `DELETE` | `/papers/api/{id}` | 删除论文 |
| `POST` | `/papers/api/download-pdf/{id}` | 下载 PDF 并提取文本 |

#### AI 分析

| 方法 | 端点 | 说明 |
|------|------|------|
| `GET` | `/analysis/status` | 检查 DeepSeek API 状态 |
| `POST` | `/analysis/analyze/stream` | 流式摘要分析 |
| `POST` | `/analysis/analyze/fulltext/stream` | 流式全文分析 |
| `POST` | `/analysis/qa/ask/stream` | 流式问答 |
| `GET` | `/analysis/qa/history/{title}` | 获取问答历史 |
| `DELETE` | `/analysis/qa/delete/{title}` | 删除问答历史 |

### API 使用示例

```bash
# 搜索论文
curl "http://localhost:8000/api/search?query=machine+learning&max_results=5"

# 按作者搜索
curl "http://localhost:8000/api/search/author?author=Hinton"

# 按分类搜索
curl "http://localhost:8000/api/search/category?category=cs.AI"

# 保存论文
curl -X POST "http://localhost:8000/papers/api/save/2312.12345"

# 下载 PDF 并提取文本
curl -X POST "http://localhost:8000/papers/api/download-pdf/2312.12345"

# 检查 DeepSeek API 状态
curl "http://localhost:8000/analysis/status"

# 流式分析摘要
curl -X POST "http://localhost:8000/analysis/analyze/stream" \
  -H "Content-Type: application/json" \
  -d '{"paper_id": "2312.12345", "title": "Paper Title", "abstract": "...", "prompt": "总结主要贡献"}'
```

## 🛠️ Development

### 开发模式运行

```bash
# 启用自动重载
DEBUG=True python run.py
```

### 运行测试

```bash
pytest tests/
```

## 📝 Notes

- 本应用使用 [arXiv API](https://arxiv.org/help/api/index) 获取论文数据
- 请遵守 arXiv 的速率限制（默认：请求间隔 3 秒）
- arXiv 是预印本仓库，论文未经同行评审
- AI 分析功能需要有效的 DeepSeek API Key
- 所有数据（论文、PDF、分析报告、问答历史）均存储在 `data/` 目录

## 🔧 Troubleshooting

### DeepSeek API 相关

**Q: 提示 "DeepSeek API is not configured"**
A: 请确保已设置环境变量 `DEEPSEEK_API_KEY`，可以通过 `.env` 文件或直接导出：
```bash
export DEEPSEEK_API_KEY=sk-your-api-key
```

**Q: AI 分析超时或失败**
A: DeepSeek reasoner 模型处理复杂分析可能需要较长时间，请耐心等待。如果频繁失败，检查网络连接或 API 配额。

**Q: 数学公式显示不正确**
A: 应用使用 KaTeX 渲染数学公式，支持 `$...$`、`$$...$$`、`\(...\)`、`\[...\]` 格式。

### 其他问题

**Q: PDF 文本提取失败**
A: 确保已安装 PyMuPDF（`pip install pymupdf`），部分扫描版 PDF 可能无法提取文本。

## 🙏 Acknowledgments

- [arXiv.org](https://arxiv.org/) - 开放获取的研究论文平台
- [DeepSeek](https://www.deepseek.com/) - 强大的 AI 模型提供商
- [FastAPI](https://fastapi.tiangolo.com/) - 优秀的 Web 框架
- [KaTeX](https://katex.org/) - 快速的数学公式渲染库
- [marked](https://marked.js.org/) - Markdown 解析器
- [highlight.js](https://highlightjs.org/) - 代码语法高亮

## 📄 License

本项目采用 [MIT License](LICENSE) 开源协议。

---

Made with ❤️ for researchers and developers
