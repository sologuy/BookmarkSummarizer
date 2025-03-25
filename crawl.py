# Copyright 2024 wyj
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import argparse
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from dotenv import load_dotenv
from urllib3.util.retry import Retry
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import chardet
from tqdm import tqdm
import traceback


# Chrome 书签文件路径
bookmark_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Bookmarks")
bookmarks_path = os.path.expanduser("./bookmarks.json")
bookmarks_with_content_path = os.path.expanduser("./bookmarks_with_content.json")
failed_urls_path = os.path.expanduser("./failed_urls.json")

# 加载环境变量
load_dotenv()

# 配置项
class ModelConfig:
    # 支持的模型类型
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    OLLAMA = "ollama"  # 添加Ollama模型类型

    def __init__(self):
        # 默认配置
        self.model_type = os.getenv("MODEL_TYPE", self.OPENAI)
        self.api_key = os.getenv("API_KEY", "")
        self.api_base = os.getenv("API_BASE", "https://api.openai.com/v1")
        self.model_name = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1000"))
        self.max_input_content_length = int(os.getenv("MAX_INPUT_CONTENT_LENGTH", "6000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.3"))
        
        # DeepSeek特定配置
        self.top_p = float(os.getenv("TOP_P", "0.7"))
        self.top_k = int(os.getenv("TOP_K", "50"))
        self.frequency_penalty = float(os.getenv("FREQUENCY_PENALTY", "0.5"))
        self.system_prompt = os.getenv("SYSTEM_PROMPT", "")
        self.use_tools = os.getenv("USE_TOOLS", "").lower() in ("true", "1", "yes")
        
        # Qwen特定配置
        self.qwen_api_version = os.getenv("QWEN_API_VERSION", "2023-12-01-preview")
        # Ollama特定配置
        self.ollama_format = os.getenv("OLLAMA_FORMAT", "text")  # 可选: json, text

# 使用大模型生成摘要
def generate_summary(title, content, url, config=None):
    """
    使用大模型生成网页内容摘要
    
    参数:
        title (str): 网页标题
        content (str): 网页内容
        url (str): 网页URL
        config (ModelConfig, optional): 模型配置，默认使用环境变量
        
    返回:
        str: 生成的摘要
    """
    if config is None:
        config = ModelConfig()
    
    try:
        # 限制内容长度，避免超出token限制
        max_content_length = config.max_input_content_length
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        # 构建更详细的提示词
        prompt = f"""请为以下网页内容生成一个全面、信息丰富的摘要（约500字）。

网页标题: {title}
网页地址: {url}

网页内容:
{content}

摘要要求:
1. 以关键信息密集的方式组织内容，确保包含重要的专业术语、实体名称和关键概念
2. 使用清晰的段落结构，按主题划分信息，每段聚焦一个核心要点
3. 在摘要开头提供一句概括性总结，简明扼要地说明文档的主要内容和目的
4. 使用事实性、具体的表述，避免模糊或一般性描述
5. 保留原文中的重要数字、日期、名称、专业术语和独特标识符
6. 对于技术内容，包含具体的技术名称、版本号、参数和方法名称
7. 对于新闻事件，明确包含时间、地点、人物和事件关键细节
8. 对于教程或指南，列出具体步骤名称和关键操作点
9. 对于产品或服务，包含具体的产品名称、特性和规格
10. 确保信息密度高，便于向量检索匹配

请生成一个信息密集、结构清晰的摘要，优化为便于向量检索的文本形式格式，尽量减少语气词、废话、重复、无用、比如：好的、嗯等词语。
"""
        # 根据不同的模型类型调用不同的API
        if config.model_type == ModelConfig.OLLAMA:
            return call_ollama_api(prompt, config)
        elif config.model_type == ModelConfig.QWEN:
            return call_qwen_api(prompt, config)
        elif config.model_type == ModelConfig.DEEPSEEK:
            return call_deepseek_api(prompt, config)
        else:
            raise ValueError(f"不支持的模型类型: {config.model_type}")
    
    except Exception as e:
        print(f"生成摘要失败: {url} - {e}")
        return f"摘要生成失败: {str(e)}"

# Ollama的API调用
def call_ollama_api(prompt, config=None):
    """
    专门为Ollama部署的模型设计的API调用
    
    参数:
        prompt (str): 提示词
        config (ModelConfig, optional): 模型配置
        
    返回:
        str: 模型生成的响应文本
    """
    if config is None:
        config = ModelConfig()
    
    # 确定是使用chat还是generate接口
    use_chat_api = True
    
    # API端点
    if use_chat_api:
        url = f"{config.api_base}/api/chat"
    else:
        url = f"{config.api_base}/api/generate"
    
    # 构建请求负载
    if use_chat_api:
        # 使用chat接口
        messages = [{"role": "user", "content": prompt}]
        
        # 如果有系统提示，添加到消息中
        if hasattr(config, 'system_prompt') and config.system_prompt:
            messages.insert(0, {"role": "system", "content": config.system_prompt})
        
        payload = {
            "model": config.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "num_predict": config.max_tokens
            }
        }
    else:
        # 使用generate接口
        system_prompt = config.system_prompt if hasattr(config, 'system_prompt') and config.system_prompt else ""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        payload = {
            "model": config.model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "top_k": config.top_k,
                "num_predict": config.max_tokens
            }
        }
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        # 发送请求
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=120  # 增加超时时间，本地模型可能需要更长处理时间
        )
        
        # 检查响应状态
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        
        # 提取生成的文本 - Ollama API格式
        if use_chat_api:
            if "message" in result:
                return result["message"]["content"]
            elif "response" in result:
                return result["response"]
        else:
            if "response" in result:
                return result["response"]
        
        # 如果找不到预期的字段，返回整个响应
        return str(result)
            
    except requests.exceptions.RequestException as e:
        print(f"Ollama API请求错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise Exception(f"API调用失败: {str(e)}")
    except ValueError as e:
        print(f"Ollama API响应解析错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise Exception(f"响应解析失败: {str(e)}")
    except Exception as e:
        print(f"Ollama API调用未知错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise 
      
# 通义千问Qwen的API调用
def call_qwen_api(prompt, config=None):
    """
    专门为通义千问Qwen2.5设计的API调用
    
    参数:
        prompt (str): 提示词
        config (ModelConfig, optional): 模型配置
        
    返回:
        str: 模型生成的响应文本
    """
    if config is None:
        config = ModelConfig()
    
    # API端点
    url = f"{config.api_base}/chat/completions"
    
    # 构建消息
    messages = [{"role": "user", "content": prompt}]
    
    # 如果有系统提示，添加到消息中
    if hasattr(config, 'system_prompt') and config.system_prompt:
        messages.insert(0, {"role": "system", "content": config.system_prompt})
    
    # 构建请求负载 - Qwen2.5 通常兼容 OpenAI 格式
    payload = {
        "model": config.model_name,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "top_p": config.top_p,
        "stream": False
    }
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    # 如果有API密钥，添加到请求头
    if config.api_key and config.api_key.strip():
        headers["Authorization"] = f"Bearer {config.api_key}"
    
    try:
        # 发送请求
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60
        )
        
        # 检查响应状态
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        
        # 提取生成的文本 - Qwen API 通常遵循 OpenAI 格式
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                return result["choices"][0]["message"]["content"]
            elif "text" in result["choices"][0]:
                return result["choices"][0]["text"]
            else:
                # 如果找不到预期的字段，返回整个choice对象
                return str(result["choices"][0])
        else:
            # 如果响应中没有choices字段，返回整个响应
            return str(result)
            
    except requests.exceptions.RequestException as e:
        print(f"Qwen API请求错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise Exception(f"API调用失败: {str(e)}")
    except ValueError as e:
        print(f"Qwen API响应解析错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise Exception(f"响应解析失败: {str(e)}")
    except Exception as e:
        print(f"Qwen API调用未知错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise

def call_deepseek_api(prompt, config=None):
    """
    专门为DeepSeek R1设计的API调用
    
    参数:
        prompt (str): 提示词
        config (ModelConfig, optional): 模型配置
        
    返回:
        str: 模型生成的响应文本
    """
    if config is None:
        config = ModelConfig()
    
    # API端点
    url = f"{config.api_base}/chat/completions"
    print(f"调用DeepSeek API: {url}")
    print(f"使用模型: {config.model_name}")
    print(f"API密钥长度: {len(config.api_key) if config.api_key else 0}")
    
    # 构建消息
    messages = [{"role": "user", "content": prompt}]
    
    # 如果有系统提示，添加到消息中
    if hasattr(config, 'system_prompt') and config.system_prompt:
        messages.insert(0, {"role": "system", "content": config.system_prompt})
    
    # 构建请求负载
    payload = {
        "model": config.model_name,  # 例如 "deepseek-ai/DeepSeek-R1"
        "messages": messages,
        "stream": False,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "top_p": getattr(config, 'top_p', 0.7),
        "top_k": getattr(config, 'top_k', 50),
        "frequency_penalty": getattr(config, 'frequency_penalty', 0.5),
        "n": 1,
        "response_format": {"type": "text"}
    }
    
    # 打印请求体以供调试
    print(f"请求配置: temperature={config.temperature}, max_tokens={config.max_tokens}")
    
    # 构建请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    # 如果有API密钥，添加到请求头
    if config.api_key and config.api_key.strip():
        headers["Authorization"] = f"Bearer {config.api_key}"
        print("已添加Authorization头")
    else:
        print("未设置API密钥，请求不包含Authorization头")
    
    try:
        # 发送请求
        print("正在发送请求...")
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=60  # 增加超时时间，因为大模型可能需要更长时间处理
        )
        
        # 检查响应状态
        print(f"响应状态码: {response.status_code}")
        response.raise_for_status()
        
        # 解析响应
        result = response.json()
        print(f"成功获取响应: {result.keys() if isinstance(result, dict) else '非字典响应'}")
        
        # 提取生成的文本
        if "choices" in result and len(result["choices"]) > 0:
            if "message" in result["choices"][0]:
                content = result["choices"][0]["message"]["content"]
                print(f"成功提取内容，长度: {len(content)}")
                return content
            elif "text" in result["choices"][0]:
                text = result["choices"][0]["text"]
                print(f"成功提取文本，长度: {len(text)}")
                return text
            else:
                # 如果找不到预期的字段，返回整个choice对象
                print(f"未找到content或text字段，返回整个choice对象: {result['choices'][0]}")
                return str(result["choices"][0])
        else:
            # 如果响应中没有choices字段，返回整个响应
            print(f"响应中没有choices字段，返回整个响应: {result}")
            return str(result)
            
    except requests.exceptions.RequestException as e:
        print(f"DeepSeek API请求错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise Exception(f"API调用失败: {str(e)}")
    except ValueError as e:
        print(f"DeepSeek API响应解析错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise Exception(f"响应解析失败: {str(e)}")
    except Exception as e:
        print(f"DeepSeek API调用未知错误: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"响应内容: {response.text}")
        raise

def test_api_connection(config=None):
    """测试API连接是否正常"""
    if config is None:
        config = ModelConfig()
    
    print(f"==== API连接测试 ====")
    print(f"模型类型: {config.model_type}")
    print(f"API基础URL: {config.api_base}")
    print(f"模型名称: {config.model_name}")
    print(f"API密钥长度: {len(config.api_key) if config.api_key else 0}")
    
    try:
        # 简单的测试提示
        test_prompt = "你是谁。请简短回答。"
        print(f"测试提示: '{test_prompt}'")
        
        print(f"开始测试API连接...")
        response = None
        
        # 根据模型类型调用相应的API
        if config.model_type == ModelConfig.OLLAMA:
            print(f"使用Ollama API")
            response = call_ollama_api(test_prompt, config)
        elif config.model_type == ModelConfig.QWEN:
            print(f"使用Qwen API")
            response = call_qwen_api(test_prompt, config)
        elif config.model_type == ModelConfig.DEEPSEEK:
            print(f"使用DeepSeek API")
            response = call_deepseek_api(test_prompt, config)
        else:
            # 其他模型类型的处理...
            print(f"未识别的模型类型: {config.model_type}，尝试使用DeepSeek API")
            response = call_deepseek_api(test_prompt, config)
        
        # 检查响应
        if response and isinstance(response, str) and len(response) > 0:
            print("✅ API连接测试成功!")
            print(f"模型响应: {response[:100]}...")
            return True
        else:
            print(f"❌ API返回空响应或无效响应: {response}")
            return False
            
    except Exception as e:
        print(f"❌ API连接测试失败: {str(e)}")
        traceback_str = traceback.format_exc()
        print(f"详细错误信息: {traceback_str}")
        return False

# 在主函数中添加摘要生成步骤
def generate_summaries_for_bookmarks(bookmarks_with_content, model_config=None):
    """为书签内容生成摘要"""
    if model_config is None:
        model_config = ModelConfig()
    
    total_count = len(bookmarks_with_content)
    print(f"正在使用 {model_config.model_type} 模型 {model_config.model_name} 生成内容摘要，共 {total_count} 个...")
    
    # 首先读取现有的文件内容
    try:
        with open(bookmarks_with_content_path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
            # 创建URL到书签的映射
            existing_map = {item.get('url'): item for item in existing_data}
    except (FileNotFoundError, json.JSONDecodeError):
        existing_map = {}
        existing_data = []

    # 使用临时文件来保存进度
    temp_file_path = f"{bookmarks_with_content_path}.temp"
    
    # 复制现有数据到临时文件
    try:
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"创建临时文件失败: {str(e)}")
        return existing_data  # 返回现有数据
    
    success_count = 0
    for idx, bookmark in enumerate(tqdm(bookmarks_with_content, desc="摘要生成进度")):
        url = bookmark["url"]
        title = bookmark["title"]
        
        # 检查是否已经处理过
        if url in existing_map and "summary" in existing_map[url]:
            print(f"[{idx+1}/{total_count}] 跳过已存在摘要: {title} - {url}")
            success_count += 1
            continue
        
        progress_info = f"[{idx+1}/{total_count}]"
        print(f"{progress_info} 正在为以下链接生成摘要: {url}")
        
        # 生成摘要
        summary = generate_summary(title, bookmark["content"], url, model_config)
        print(f"{progress_info} title: {title}")
        print(f"{progress_info} 摘要长度: {len(summary)} 字符")
        
        # 添加摘要到书签数据
        bookmark["summary"] = summary
        bookmark["summary_model"] = model_config.model_name
        bookmark["summary_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if "摘要生成失败" not in summary:
            success_count += 1
            print(f"{progress_info} 摘要生成成功")
            
            # 更新数据结构
            if url in existing_map:
                # 更新现有记录
                for i, item in enumerate(existing_data):
                    if item.get('url') == url:
                        existing_data[i] = bookmark
                        break
            else:
                # 添加新记录
                existing_data.append(bookmark)
            
            # 保存到临时文件
            try:
                with open(temp_file_path, 'w', encoding='utf-8') as f:
                    json.dump(existing_data, f, ensure_ascii=False, indent=4)
                # 成功写入临时文件后，替换原文件
                os.replace(temp_file_path, bookmarks_with_content_path)
                print(f"{progress_info} 已保存当前进度")
            except Exception as e:
                print(f"{progress_info} 保存进度时出错: {str(e)}")
        else:
            print(f"{progress_info} 摘要生成失败: {summary}")
        
        # 每次请求后短暂暂停，避免API限制
        time.sleep(0.5)
    
    print(f"摘要生成完成! 成功: {success_count}/{total_count}")
    return existing_data

# 读取书签 JSON 文件
def get_bookmarks(bookmark_path):
    with open(bookmark_path, "r", encoding="utf-8") as file:
        bookmarks_data = json.load(file)

    urls = []

    def extract_bookmarks(bookmark_node):
        """递归提取所有书签的 URL"""
        if "children" in bookmark_node:
            for child in bookmark_node["children"]:
                extract_bookmarks(child)
        elif "url" in bookmark_node:
            bookmark_info = {
                "date_added": bookmark_node.get("date_added", "N/A"),
                "date_last_used": bookmark_node.get("date_last_used", "N/A"),
                "guid": bookmark_node.get("guid", "N/A"),
                "id": bookmark_node.get("id", "N/A"),
                "name": bookmark_node.get("name", "N/A"),
                "type": bookmark_node.get("type", "url"),
                "url": bookmark_node.get("url", ""),
            }
            urls.append(bookmark_info)

    # 遍历 JSON 结构
    for item in bookmarks_data["roots"].values():
        extract_bookmarks(item)

    return urls

# 创建一个带有重试机制的会话
def create_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # 最多重试3次
        backoff_factor=0.5,  # 重试间隔时间
        status_forcelist=[429, 500, 502, 503, 504],  # 这些状态码会触发重试
        allowed_methods=["GET"]  # 只对GET请求进行重试
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# 清理文本内容
def clean_text(text):
    # 移除多余的空白行和空格
    lines = [line.strip() for line in text.split('\n')]
    # 过滤掉空行
    lines = [line for line in lines if line]
    # 合并行
    return '\n'.join(lines)

# 初始化Selenium WebDriver
def init_webdriver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无头模式
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # 添加更多的用户代理信息
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
    
    # 禁用图片加载以提高速度
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

# 使用Selenium爬取动态内容
def fetch_with_selenium(url, current_idx=None, total_count=None, title="无标题"):
    """使用Selenium获取网页内容"""
    progress_info = f"[{current_idx}/{total_count}]" if current_idx and total_count else ""
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 添加更真实的用户代理
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36')
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        print(f"{progress_info} 开始使用Selenium爬取：{title} - {url}")
        driver.get(url)
        
        # 等待页面加载
        time.sleep(5)
        
        # 知乎特殊处理：如果有登录弹窗，尝试关闭
        if "zhihu.com" in url:
            try:
                # 尝试点击关闭按钮 (多种可能的选择器)
                selectors = ['.Modal-closeButton', '.Button.Modal-closeButton', 
                            'button.Button.Modal-closeButton', '.close']
                for selector in selectors:
                    try:
                        close_button = driver.find_element("css selector", selector)
                        close_button.click()
                        print(f"{progress_info} 成功关闭知乎登录弹窗 - 使用选择器: {selector}")
                        time.sleep(1)
                        break
                    except:
                        continue
            except Exception as e:
                print(f"{progress_info} 处理知乎登录弹窗失败: {title} - {str(e)}")
        
        # 获取页面内容
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        
        # 知乎特殊处理：提取文章内容
        if "zhihu.com" in url:
            article = soup.select_one('.Post-RichText') or soup.select_one('.RichText') or soup.select_one('.AuthorInfo') or soup.select_one('article')
            if article:
                text_content = article.get_text(strip=True)
            else:
                text_content = soup.get_text(strip=True)
        else:
            # 一般网页处理
            text_content = soup.get_text(strip=True)
        
        # 修复编码问题
        text_content = fix_encoding(text_content)
        
        # 确保文本不为空
        if not text_content or len(text_content.strip()) < 5:  # 至少5个字符才算有效内容
            print(f"{progress_info} Selenium爬取内容为空或太少: {title} - {url}")
            return None
            
        print(f"{progress_info} Selenium成功爬取: {title} - {url}，内容长度: {len(text_content)} 字符")
        return text_content
        
    except Exception as e:
        print(f"{progress_info} Selenium爬取失败: {title} - {url} - {str(e)}")
        return None
    finally:
        if 'driver' in locals():
            driver.quit()

# 检测并修复编码问题 优化后的编码修复函数
def fix_encoding(text):
    """
    检测并修复文本编码问题，优化性能版本
    """
    if not text or len(text) < 20:  # 对短文本直接返回
        return text
    
    # 快速检查是否需要修复 - 只检查文本的一小部分样本
    sample_size = min(1000, len(text))
    sample_text = text[:sample_size]
    
    # 如果样本中非ASCII字符比例低，直接返回原文本
    non_ascii_count = sum(1 for c in sample_text if ord(c) > 127)
    if non_ascii_count < sample_size * 0.1:  # 如果非ASCII字符少于10%
        return text
    
    # 检查是否有明显的编码问题特征（连续的特殊字符）
    # 使用更高效的方法替代正则表达式
    special_char_sequence = 0
    for c in sample_text:
        if ord(c) > 127:
            special_char_sequence += 1
            if special_char_sequence >= 10:  # 发现连续10个非ASCII字符
                break
        else:
            special_char_sequence = 0
    
    # 如果没有明显的编码问题特征，直接返回
    if special_char_sequence < 10:
        return text
    
    # 只对可能有问题的文本进行编码检测
    try:
        # 只对样本进行编码检测，而不是整个文本
        sample_bytes = sample_text.encode('latin-1', errors='ignore')
        detected = chardet.detect(sample_bytes)
        
        # 如果检测到的编码与当前编码不同且置信度高
        if detected['confidence'] > 0.8 and detected['encoding'] not in ('ascii', 'utf-8'):
            # 对整个文本进行重新编码
            text_bytes = text.encode('latin-1', errors='ignore')
            return text_bytes.decode(detected['encoding'], errors='replace')
    except Exception as e:
        print(f"编码修复失败: {e}")
    
    return text

# 爬取网页内容
def fetch_webpage_content(bookmark, current_idx=None, total_count=None):
    """爬取网页内容"""
    url = bookmark["url"]
    title = bookmark.get("name", "无标题")  # 从书签中获取标题
    progress_info = f"[{current_idx}/{total_count}]" if current_idx and total_count else ""
    
    # 初始化变量，防止未赋值
    content = None
    crawl_method = None
    
    # 知乎链接直接使用Selenium
    if "zhihu.com" in url:
        print(f"{progress_info} 检测到知乎链接，直接使用Selenium爬取: {title} - {url}")
        content = fetch_with_selenium(url, current_idx, total_count, title)
        crawl_method = "selenium"
        
        # 记录爬取结果
        if content:
            print(f"{progress_info} 成功爬取知乎内容: {title} - {url}，内容长度: {len(content)} 字符")
        else:
            print(f"{progress_info} 爬取知乎内容失败: {title} - {url}")
            return None, {"url": url, "title": title, "reason": "知乎内容爬取失败", "timestamp": datetime.now().isoformat()}
    else:
        try:
            print(f"{progress_info} 开始爬取: {title} - {url}")
            session = create_session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            # 检测响应内容的编码
            detected_encoding = chardet.detect(response.content)
            if detected_encoding['confidence'] > 0.7:
                response.encoding = detected_encoding['encoding']
            
            # 检查内容类型，确保是HTML或文本
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type.lower() and 'text/plain' not in content_type.lower():
                error_msg = f"非文本内容 (Content-Type: {content_type})"
                print(f"{progress_info} 跳过{error_msg}: {title} - {url}")
                failed_info = {"url": url, "title": title, "reason": error_msg, "timestamp": datetime.now().isoformat()}
                return None, failed_info
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 提取标题
            if soup.title:
                title = soup.title.string if soup.title.string else "无标题"
            else:
                title = "无标题"
            
            # 移除不需要的元素，如脚本、样式、导航等
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'meta', 'link']):
                element.decompose()
            
            # 直接获取整个页面的文本内容
            full_text = soup.get_text(separator='\n')
            
            # 清理文本
            content = clean_text(full_text)
            crawl_method = "requests"
        except Exception as e:
            error_msg = f"请求失败: {str(e)}"
            print(f"{progress_info} {error_msg}: {title} - {url}")
            failed_info = {"url": url, "title": title, "reason": error_msg, "timestamp": datetime.now().isoformat()}
            return None, failed_info
    
    # 特殊网站或常规爬取失败，尝试使用Selenium
    if content is None or (isinstance(content, str) and not content.strip()):
        print(f"{progress_info} 常规爬取内容为空，尝试使用Selenium: {title} - {url}")
        content = fetch_with_selenium(url, current_idx, total_count, title)
        crawl_method = "selenium"
        
        # 记录Selenium爬取结果
        if content:
            print(f"{progress_info} Selenium成功爬取 {url}，内容长度: {len(content)} 字符")
        else:
            print(f"{progress_info} Selenium爬取失败或内容为空: {url}")
    
    # 修复可能的编码问题
    if title:
        title = fix_encoding(title)
    else:
        title = "无标题"
        
    if content and isinstance(content, str):
        content = fix_encoding(content)
    else:
        content = ""
    
    # 检查内容是否为空
    if not content or not content.strip():
        error_msg = "提取的内容为空"
        print(f"{progress_info} {error_msg}: {title} - {url}")
        failed_info = {"url": url, "title": title, "reason": error_msg, "timestamp": datetime.now().isoformat()}
        return None, failed_info
            
    # 创建包含内容的书签副本
    bookmark_with_content = bookmark.copy()
    bookmark_with_content["title"] = title
    bookmark_with_content["content"] = content
    bookmark_with_content["content_length"] = len(content)
    bookmark_with_content["crawl_time"] = datetime.now().isoformat()
    bookmark_with_content["crawl_method"] = crawl_method
    
    print(f"{progress_info} 成功爬取: {title} - {url}，内容长度: {len(content)} 字符")
    return bookmark_with_content, None

# 并行爬取书签内容
def parallel_fetch_bookmarks(bookmarks, max_workers=20, limit=None):
    if limit:
        print(f"根据配置限制，只处理前 {limit} 个书签")
        bookmarks_to_process = bookmarks[:limit]
    else:
        print(f"处理全部 {len(bookmarks)} 个书签")
        bookmarks_to_process = bookmarks
    
    bookmarks_with_content = []
    failed_records = []
    
    # 使用 ThreadPoolExecutor 并行爬取书签内容
    start_time = time.time()
    total_count = len(bookmarks_to_process)
    print(f"开始并行爬取书签内容，最大并发数: {max_workers}，总数: {total_count}")
    print(f"开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建一个列表来存储所有任务
    futures = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        for idx, bookmark in enumerate(bookmarks_to_process):
            # 在提交任务前打印进度
            title = bookmark.get("name", "无标题")
            print(f"提交任务 [{idx+1}/{total_count}]: {title} - {bookmark['url']}")
            future = executor.submit(fetch_webpage_content, bookmark, idx+1, total_count)
            futures.append(future)
        
        # 使用tqdm创建进度条
        for future in tqdm(futures, total=len(futures), desc="爬取进度"):
            result, failed_info = future.result()
            if result:
                bookmarks_with_content.append(result)
            if failed_info:
                failed_records.append(failed_info)
    
    end_time = time.time()
    print(f"结束时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 打印耗时信息
    elapsed_time = end_time - start_time
    elapsed_minutes = elapsed_time / 60
    if elapsed_time > 60:
        print(f"并行爬取书签内容总耗时: {elapsed_minutes:.2f}分钟 ({elapsed_time:.2f}秒)")
    else:
        print(f"并行爬取书签内容总耗时: {elapsed_time:.2f}秒")
    
    # 计算每个书签的平均处理时间
    if total_count > 0:
        avg_time_per_bookmark = elapsed_time / total_count
        print(f"平均每个书签处理时间: {avg_time_per_bookmark:.2f}秒")
    
    return bookmarks_with_content, failed_records

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='爬取Chrome书签并构建知识库')
    parser.add_argument('--limit', type=int, help='限制处理的书签数量，0表示不限制')
    parser.add_argument('--workers', type=int, help='并行爬取的工作线程数')
    parser.add_argument('--no-summary', action='store_true', help='跳过摘要生成步骤')
    parser.add_argument('--from-json', action='store_true', help='从已有的bookmarks_with_content.json生成摘要')
    return parser.parse_args()

# 主函数
def main():
    # 解析命令行参数
    args = parse_args()
    
    # 从环境变量读取配置，命令行参数优先
    bookmark_limit = args.limit if args.limit is not None else int(os.getenv("BOOKMARK_LIMIT", "0"))  # 默认不限制
    max_workers = args.workers if args.workers is not None else int(os.getenv("MAX_WORKERS", "20"))  # 默认20个工作线程
    generate_summary = not args.no_summary if args.no_summary is not None else os.getenv("GENERATE_SUMMARY", "true").lower() in ("true", "1", "yes")  # 默认生成摘要
    
    # 如果使用--from-json参数，直接从JSON文件读取并生成摘要
    if args.from_json:
        print("从已有的bookmarks_with_content.json生成摘要...")
        try:
            with open(bookmarks_with_content_path, 'r', encoding='utf-8') as f:
                bookmarks_with_content = json.load(f)
            
            if not bookmarks_with_content:
                print("错误：bookmarks_with_content.json为空或格式不正确")
                return
                
            if bookmark_limit > 0:
                print(f"根据限制只处理前{bookmark_limit}个书签")
                bookmarks_with_content = bookmarks_with_content[:bookmark_limit]
                
            # 配置模型并生成摘要
            model_config = ModelConfig()
            
            # 测试API连接
            if not test_api_connection(model_config):
                print("LLM API连接失败，请检查配置后重试。", model_config.api_base, model_config.model_name, model_config.api_key, model_config.model_type)
                return
                
            # 为内容生成摘要
            bookmarks_with_content = generate_summaries_for_bookmarks(bookmarks_with_content, model_config)
            
            # 保存更新后的内容
            with open(bookmarks_with_content_path, "w", encoding="utf-8") as output_file:
                json.dump(bookmarks_with_content, output_file, ensure_ascii=False, indent=4)
                
            print(f"摘要生成完成，已更新 {bookmarks_with_content_path}")
            return
            
        except FileNotFoundError:
            print(f"错误：找不到文件 {bookmarks_with_content_path}")
            return
        except json.JSONDecodeError:
            print(f"错误：{bookmarks_with_content_path} 不是有效的JSON文件")
            return
        except Exception as e:
            print(f"处理JSON文件时出错：{str(e)}")
            return
    
    # 原有的爬取逻辑
    print(f"配置信息:")
    print(f"  - 书签数量限制: {bookmark_limit if bookmark_limit > 0 else '不限制'}")
    print(f"  - 并行工作线程: {max_workers}")
    print(f"  - 是否生成摘要: {'是' if generate_summary else '否'}")
    
    # 获取书签数据
    bookmarks = get_bookmarks(bookmark_path)
    
    # 过滤书签，去除空 URL、10.0.网段的URL和不符合条件的
    filtered_bookmarks = []
    for bookmark in bookmarks:
        url = bookmark["url"]
        # 检查是否为空URL、是否包含taihealth、是否为URL类型、是否为扩展程序、是否为10.0.网段
        if (url and 
            bookmark["type"] == "url" and 
            bookmark["name"] != "扩展程序" and
            not re.match(r"https?://10\.0\.", url)):
            filtered_bookmarks.append(bookmark)
    
    # 保存过滤后的书签数据
    with open(bookmarks_path, "w", encoding="utf-8") as output_file:
        json.dump(filtered_bookmarks, output_file, ensure_ascii=False, indent=4)
    
    # 并行爬取书签内容
    bookmarks_with_content, failed_records = parallel_fetch_bookmarks(
        filtered_bookmarks, 
        max_workers=max_workers, 
        limit=bookmark_limit if bookmark_limit > 0 else None
    )
    
    # 只有在需要生成摘要时才执行下面的代码
    if generate_summary and bookmarks_with_content:
        # 配置模型
        model_config = ModelConfig()
        
        # 测试API连接
        if not test_api_connection(model_config):
            print("LLM API连接失败，请检查配置后重试。", model_config.api_base, model_config.model_name, model_config.api_key, model_config.model_type)
            print("跳过摘要生成步骤...")
        else:
            # 为爬取的内容生成摘要
            bookmarks_with_content = generate_summaries_for_bookmarks(bookmarks_with_content, model_config)
    elif not generate_summary:
        print("根据配置跳过摘要生成步骤...")

    # 保存带内容的书签数据
    with open(bookmarks_with_content_path, "w", encoding="utf-8") as output_file:
        json.dump(bookmarks_with_content, output_file, ensure_ascii=False, indent=4)
    
    # 保存失败的URL及原因
    with open(failed_urls_path, "w", encoding="utf-8") as f:
        json.dump(failed_records, f, ensure_ascii=False, indent=4)
    
    print(f"共提取 {len(filtered_bookmarks)} 个有效书签，已保存到 {bookmarks_path}")
    print(f"成功爬取 {len(bookmarks_with_content)} 个书签的内容，已保存到 {bookmarks_with_content_path}")
    print(f"爬取失败 {len(failed_records)} 个URL，详细信息已保存到 {failed_urls_path}")
    
    # 打印失败的URL及标题列表，便于查看
    if failed_records:
        print("\n爬取失败的URL及标题:")
        for idx, record in enumerate(failed_records):
            print(f"{idx+1}. {record.get('title', '无标题')} - {record['url']} - 原因: {record['reason']}")
    
    # 显示内容长度统计
    if bookmarks_with_content:
        total_length = sum(b.get("content_length", 0) for b in bookmarks_with_content)
        avg_length = total_length / len(bookmarks_with_content)
        print(f"爬取内容平均长度: {avg_length:.2f} 字符")
        print(f"最长内容: {max(b.get('content_length', 0) for b in bookmarks_with_content)} 字符")
        print(f"最短内容: {min(b.get('content_length', 0) for b in bookmarks_with_content)} 字符")
        
        # 统计使用的爬取方法
        selenium_count = sum(1 for b in bookmarks_with_content if b.get("crawl_method") == "selenium")
        requests_count = sum(1 for b in bookmarks_with_content if b.get("crawl_method") == "requests")
        print(f"使用Selenium爬取: {selenium_count} 个")
        print(f"使用Requests爬取: {requests_count} 个")

def fetch_zhihu_content(url, current_idx=None, total_count=None, title="无标题"):
    """专门处理知乎链接"""
    progress_info = f"[{current_idx}/{total_count}]" if current_idx and total_count else ""
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 添加更真实的用户代理
    options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        print(f"{progress_info} 使用专门方法爬取知乎内容: {title} - {url}")
        driver.get(url)
        # 等待页面加载
        time.sleep(3)
        
        # 检测登录弹窗并关闭
        try:
            login_close = driver.find_element_by_css_selector('.Modal-closeButton')
            login_close.click()
            print(f"{progress_info} 成功关闭知乎登录弹窗")
            time.sleep(1)
        except Exception as e:
            print(f"{progress_info} 关闭知乎登录弹窗失败或无需关闭: {title} - {str(e)}")
        
        # 获取页面内容
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        
        # 提取主要内容
        article = soup.select_one('.Post-RichText') or soup.select_one('.RichText')
        if article:
            result = article.get_text()
            print(f"{progress_info} 成功提取知乎文章内容: {title}，长度: {len(result)} 字符")
            return result
        else:
            result = soup.get_text()
            print(f"{progress_info} 未找到知乎文章主体，使用全文: {title}，长度: {len(result)} 字符")
            return result
    
    except Exception as e:
        print(f"{progress_info} 知乎爬取异常: {title} - {url} - {str(e)}")
        return None
    finally:
        driver.quit()

if __name__ == "__main__":
    main()