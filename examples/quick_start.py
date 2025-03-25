#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
BookmarkSummarizer快速开始示例
"""

import os
import sys
import subprocess

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入程序
from index import get_bookmarks

def main():
    """快速开始示例"""
    # 步骤1: 提取书签
    print("步骤1: 提取Chrome书签")
    bookmark_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Bookmarks")
    
    if not os.path.exists(bookmark_path):
        print(f"错误: 找不到Chrome书签文件: {bookmark_path}")
        print("请确认Chrome已安装，或者修改bookmark_path路径")
        sys.exit(1)
    
    # 使用index.py提取书签
    bookmarks = get_bookmarks(bookmark_path)
    print(f"成功提取 {len(bookmarks)} 个书签")
    
    # 步骤2: 爬取内容并生成摘要
    print("\n步骤2: 爬取内容并生成摘要")
    print("运行以下命令开始处理:")
    print("python crawl.py --limit 5")  # 仅处理5个书签作为示例
    
    # 提示用户确认
    confirmation = input("\n是否立即开始处理5个书签? (y/n): ")
    if confirmation.lower() == 'y':
        try:
            subprocess.run(["python", "../crawl.py", "--limit", "5"], check=True)
            print("\n处理完成! 请查看生成的JSON文件")
        except subprocess.CalledProcessError as e:
            print(f"处理过程中发生错误: {e}")
    else:
        print("您可以稍后手动运行上述命令")
    
    print("\n快速开始完成!")

if __name__ == "__main__":
    main() 