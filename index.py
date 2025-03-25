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

import json
import os

# Chrome 书签文件路径
bookmark_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Bookmarks")
# 保存到 JSON 文件路径
output_path = os.path.expanduser("./bookmarks.json")

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

# 解析书签
bookmarks = get_bookmarks(bookmark_path)

# 保存到 JSON 文件
output_path = os.path.expanduser(output_path)
with open(output_path, "w", encoding="utf-8") as output_file:
    # 去掉 url 为空的数据，以及扩展程序的数据
    bookmarks = [bookmark for bookmark in bookmarks if bookmark["url"] and bookmark["type"] == "url" and bookmark["name"] != "扩展程序"] 
    json.dump(bookmarks, output_file, ensure_ascii=False, indent=4)

print(f"共提取 {len(bookmarks)} 个书签，已保存到 {output_path}")
