.PHONY: setup run run-limit crawl summarize clean help

help:
	@echo "BookmarkSummarizer 使用指南"
	@echo "make setup       - 安装依赖并准备环境"
	@echo "make run         - 运行完整流程（提取书签+爬取+摘要生成）"
	@echo "make run-limit N=10  - 限制处理10个书签"
	@echo "make crawl       - 只爬取书签内容，不生成摘要"
	@echo "make summarize   - 从已爬取内容生成摘要"
	@echo "make clean       - 清理生成的JSON文件"

setup:
	pip install -r requirements.txt
	cp .env.example .env
	@echo "请编辑 .env 文件配置您的API密钥和其他参数"

run:
	python index.py
	python crawl.py

run-limit:
	python index.py
	python crawl.py --limit $(N)

crawl:
	python index.py
	python crawl.py --no-summary

summarize:
	python crawl.py --from-json

clean:
	rm -f bookmarks.json bookmarks_with_content*.json failed_urls.json failed_urls.txt

# 默认目标
default: help 