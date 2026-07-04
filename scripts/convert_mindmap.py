"""将 NotebookLM 思维导图 JSON 转换为 FreeMind (.mm) 格式"""
import json
import sys
import os
from xml.sax.saxutils import escape

def json_to_freemind(node, depth=0):
    name = node.get("name", "")
    children = node.get("children", [])
    indent = "  " * depth
    lines = []
    # 使用 POSITION 属性让子节点在右侧展开
    pos_attr = ' POSITION="right"' if depth > 0 else ""
    if children:
        lines.append(f'{indent}<node TEXT="{escape(name)}"{pos_attr}>')
        for child in children:
            lines.append(json_to_freemind(child, depth + 1))
        lines.append(f'{indent}</node>')
    else:
        lines.append(f'{indent}<node TEXT="{escape(name)}"{pos_attr}/>')
    return "\n".join(lines)

def convert(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mm_content = f"""<map version="1.0.1">
{json_to_freemind(data)}
</map>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mm_content)
    print(f"转换完成: {output_path}")

if __name__ == "__main__":
    input_path = r"E:\工作AI\outputs\餐饮思维导图.json"
    output_path = r"E:\工作AI\outputs\餐饮思维导图.mm"
    convert(input_path, output_path)
