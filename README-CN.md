# BookmarkSummarizer (书签大脑)

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.6+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/LLM-enabled-green.svg" alt="LLM">
</p>

BookmarkSummarizer 是一个强大的工具，它能够爬取您的 Chrome 书签内容，使用大语言模型生成摘要，并将它们转化为个人知识库。无需整理，轻松搜索和利用您收藏的所有网页资源。

<p align="right"><a href="#english-documentation">English Documentation</a></p>

## ✨ 主要功能

- 🔍 **智能书签内容爬取**：自动从 Chrome 书签抓取全文内容
- 🤖 **AI 摘要生成**：用大型语言模型为每个书签创建高质量摘要
- 🔄 **并行处理**：高效的多线程爬取，显著减少处理时间
- 🌐 **多种模型支持**：兼容 OpenAI、Deepseek、Qwen 和 Ollama 等多种大语言模型
- 💾 **断点续传**：支持中断后继续处理，不会丢失已完成的工作
- 📊 **详细日志**：清晰的进度和状态报告，便于监控和调试

## 🚀 快速开始

### 前提条件

- Python 3.6+
- Chrome 浏览器
- 网络连接
- 大语言模型 API 密钥（可选）

### 安装

1. 克隆仓库:
```bash
git clone https://github.com/yourusername/BookmarkSummarizer.git
cd BookmarkSummarizer
```

2. 安装依赖:
```bash
pip install -r requirements.txt
```

3. 配置环境变量（创建 `.env` 文件）:
```
MODEL_TYPE=ollama  # 可选: openai, deepseek, qwen, ollama
API_KEY=your_api_key_here
API_BASE=http://localhost:11434  # Ollama 本地端点或其他模型 API 地址
MODEL_NAME=llama2  # 或其他支持的模型
MAX_TOKENS=1000
TEMPERATURE=0.3
```

### 使用方法

**基础用法**:
```bash
python crawl.py
```

**限制书签数量**:
```bash
python crawl.py --limit 10
```

**设置并行处理线程数**:
```bash
python crawl.py --workers 10
```

**跳过摘要生成**:
```bash
python crawl.py --no-summary
```

**从已爬取的内容生成摘要**:
```bash
python crawl.py --from-json
```

## 📋 功能详解

### 书签爬取

BookmarkSummarizer 会自动从 Chrome 书签文件中读取所有书签，并智能过滤掉不符合条件的 URL。它使用两种策略爬取网页内容:

1. **常规爬取**: 使用 Requests 库抓取大多数网页内容
2. **动态内容爬取**: 对于动态网页（如知乎等平台），自动切换到 Selenium 爬取

### 摘要生成

BookmarkSummarizer 使用先进的大语言模型为每个书签内容生成高质量摘要，包括:

- 提取关键信息和重要概念
- 保留专业术语和关键数据
- 生成结构化摘要，便于后续检索
- 支持多种主流大语言模型

### 断点续传

- 每处理完一个书签就立即保存进度
- 中断后重启时会自动跳过已处理的书签
- 即使在大量书签处理过程中，也能保证数据安全

## 📁 输出文件

- `bookmarks.json`: 过滤后的书签列表
- `bookmarks_with_content.json`: 带有内容和摘要的书签数据
- `failed_urls.json`: 爬取失败的 URL 及原因

## 🔧 自定义配置

除了命令行参数外，您还可以通过 `.env` 文件设置以下环境变量:

```
# 模型类型设置
MODEL_TYPE=ollama  # openai, deepseek, qwen, ollama
API_KEY=your_api_key_here
API_BASE=http://localhost:11434
MODEL_NAME=llama2

# 内容处理设置
MAX_TOKENS=1000  # 生成摘要的最大令牌数
MAX_INPUT_CONTENT_LENGTH=6000  # 输入内容的最大长度
TEMPERATURE=0.3  # 生成摘要的随机性

# 爬虫设置
BOOKMARK_LIMIT=0  # 默认不限制
MAX_WORKERS=20  # 并行工作线程数
GENERATE_SUMMARY=true  # 是否生成摘要
```

## 🤝 贡献

欢迎提交 Pull Requests! 有任何问题或建议，请创建 Issue。

## 📄 许可证

本项目采用 [Apache License 2.0](LICENSE) 许可证。

## 🔮 未来计划

- [ ] 添加向量数据库支持，实现语义搜索
- [ ] 开发 Web 界面，提供可视化管理
- [ ] 支持更多浏览器的书签导入
- [ ] 增加定时更新功能，保持书签内容最新
- [ ] 支持导出为知识图谱

---

<h1 id="english-documentation">BookmarkSummarizer</h1>

<p align="center">
  <img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License">
  <img src="https://img.shields.io/badge/python-3.6+-blue.svg" alt="Python">
  <img src="https://img.shields.io/badge/LLM-enabled-green.svg" alt="LLM">
</p>

BookmarkSummarizer is a powerful tool that crawls your Chrome bookmarks, generates summaries using large language models, and turns them into a personal knowledge base. Easily search and utilize all your bookmarked web resources without manual organization.

<p align="right"><a href="#bookmarkSummarizer-书签大脑">中文</a></p>

## ✨ Key Features

- 🔍 **Smart Bookmark Crawling**: Automatically extract content from Chrome bookmarks
- 🤖 **AI Summary Generation**: Create high-quality summaries for each bookmark using large language models
- 🔄 **Parallel Processing**: Efficient multi-threaded crawling to significantly reduce processing time
- 🌐 **Multiple Model Support**: Compatible with OpenAI, Deepseek, Qwen, and Ollama models
- 💾 **Checkpoint Recovery**: Continue processing after interruptions without losing completed work
- 📊 **Detailed Logging**: Clear progress and status reports for monitoring and debugging

## 🚀 Quick Start

### Prerequisites

- Python 3.6+
- Chrome browser
- Internet connection
- Large language model API key (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/BookmarkSummarizer.git
cd BookmarkSummarizer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables (create a `.env` file):
```
MODEL_TYPE=ollama  # Options: openai, deepseek, qwen, ollama
API_KEY=your_api_key_here
API_BASE=http://localhost:11434  # Ollama local endpoint or other model API address
MODEL_NAME=llama2  # Or other supported model
MAX_TOKENS=1000
TEMPERATURE=0.3
```

### Usage

**Basic usage**:
```bash
python crawl.py
```

**Limit the number of bookmarks**:
```bash
python crawl.py --limit 10
```

**Set the number of parallel processing threads**:
```bash
python crawl.py --workers 10
```

**Skip summary generation**:
```bash
python crawl.py --no-summary
```

**Generate summaries from already crawled content**:
```bash
python crawl.py --from-json
```

## 📋 Detailed Features

### Bookmark Crawling

BookmarkSummarizer automatically reads all bookmarks from the Chrome bookmarks file and intelligently filters out ineligible URLs. It uses two strategies to crawl web content:

1. **Regular Crawling**: Uses the Requests library to capture content from most web pages
2. **Dynamic Content Crawling**: For dynamic webpages (such as Zhihu and other platforms), automatically switches to Selenium

### Summary Generation

BookmarkSummarizer uses advanced large language models to generate high-quality summaries for each bookmark content, including:

- Extracting key information and important concepts
- Preserving technical terms and key data
- Generating structured summaries for easier retrieval
- Supporting various mainstream large language models

### Checkpoint Recovery

- Saves progress immediately after processing each bookmark
- Automatically skips previously processed bookmarks when restarted
- Ensures data safety even when processing large numbers of bookmarks

## 📁 Output Files

- `bookmarks.json`: Filtered bookmark list
- `bookmarks_with_content.json`: Bookmark data with content and summaries
- `failed_urls.json`: Failed URLs and reasons

## 🔧 Custom Configuration

In addition to command-line parameters, you can set the following environment variables through the `.env` file:

```
# Model Type Settings
MODEL_TYPE=ollama  # openai, deepseek, qwen, ollama
API_KEY=your_api_key_here
API_BASE=http://localhost:11434
MODEL_NAME=llama2

# Content Processing Settings
MAX_TOKENS=1000  # Maximum number of tokens for summary generation
MAX_INPUT_CONTENT_LENGTH=6000  # Maximum length of input content
TEMPERATURE=0.3  # Randomness of summary generation

# Crawler Settings
BOOKMARK_LIMIT=0  # No limit by default
MAX_WORKERS=20  # Number of parallel worker threads
GENERATE_SUMMARY=true  # Whether to generate summaries
```

## 🤝 Contributing

Pull Requests are welcome! For any issues or suggestions, please create an Issue.

## 📄 License

This project is licensed under the [Apache License 2.0](LICENSE).

## 🔮 Future Plans

- [ ] Add vector database support for semantic search
- [ ] Develop a web interface for visual management
- [ ] Support bookmark imports from more browsers
- [ ] Add scheduled update functionality to keep bookmark content current
- [ ] Support export to knowledge graphs