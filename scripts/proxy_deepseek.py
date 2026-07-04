# =============================================
# proxy_deepseek.py - DeepSeek API 代理 (Python 版)
# 将 Anthropic 消息格式转换为 OpenAI 格式转发到 DeepSeek
# 端口 3400，仅监听 127.0.0.1
# =============================================
"""Anthropic → DeepSeek API 代理（Anthropic 消息格式转 OpenAI 格式）"""
import http.server, json, urllib.request, sys

# DeepSeek API 密钥
API_KEY = "sk-2b1524f7492a4ccfab9ee924fc173397"
# DeepSeek Chat Completions 端点
TARGET = "https://api.deepseek.com/v1/chat/completions"

class Proxy(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # 读取请求体
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))

        # Anthropic messages → OpenAI messages 格式转换
        system = ""
        messages = []
        for m in body.get("messages", []):
            role = m.get("role","user")
            content = m.get("content","")
            # Anthropic content 可能是数组格式，提取纯文本
            if isinstance(content, list):
                content = " ".join(c.get("text","") for c in content if c.get("type")=="text")
            if role == "system":
                system = content
            else:
                messages.append({"role": role, "content": content})
        if system:
            messages.insert(0, {"role": "system", "content": system})

        # 构建 OpenAI 格式请求体
        req_body = {
            "model": body.get("model","deepseek-v4-pro").replace("claude-","deepseek-"),
            "messages": messages,
            "max_tokens": body.get("max_tokens", 4096),
            "temperature": body.get("temperature", 0.7),
            "stream": body.get("stream", False)
        }

        # 发送请求到 DeepSeek API
        data = json.dumps(req_body).encode()
        req = urllib.request.Request(TARGET, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        })

        try:
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read())
            choice = result["choices"][0]["message"]["content"]

            # OpenAI response → Anthropic response 格式转换
            reply = {
                "id": result.get("id","msg_001"),
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": choice}],
                "model": body.get("model","deepseek-v4-pro"),
                "stop_reason": "end_turn",
                "usage": result.get("usage",{})
            }

            self.send_response(200)
            self.send_header("Content-Type","application/json")
            self.end_headers()
            self.wfile.write(json.dumps(reply).encode())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({"error":str(e)}).encode())

    def do_GET(self):
        # 健康检查端点
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"proxy ok")

if __name__ == "__main__":
    # 支持命令行指定端口，默认 3400
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3400
    print(f"代理启动: http://127.0.0.1:{port}")
    http.server.HTTPServer(("127.0.0.1", port), Proxy).serve_forever()
