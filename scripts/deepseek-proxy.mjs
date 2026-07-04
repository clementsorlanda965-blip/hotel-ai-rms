// =============================================
// deepseek-proxy.mjs - DeepSeek API 本地代理 (Node.js)
// 将 Anthropic 格式请求转发到 DeepSeek API (端口 3200)
// 自动注入 thinking=disabled 并翻译模型名称
// =============================================

import http from "node:http";
import https from "node:https";

// DeepSeek API 地址和认证配置
const DEEPSEEK_HOST = "api.deepseek.com";
const DEEPSEEK_PATH = "/anthropic";
const API_KEY = "sk-2b1524f7492a4ccfab9ee924fc173397";

// 模型名称映射：Claude 模型 → DeepSeek 模型
const MODEL_MAP = {
  "claude-sonnet-4-6": "deepseek-v4-pro",
  "claude-sonnet-4-5": "deepseek-v4-pro",
  "claude-opus-4-7": "deepseek-v4-pro",
  "claude-opus-4-5": "deepseek-v4-pro",
  "claude-haiku-4-5": "deepseek-v4-flash",
  "claude-sonnet-4-7": "deepseek-v4-pro",
  "claude-opus-4-6": "deepseek-v4-pro",
};

// 代理监听端口
const PORT = 3200;

// 创建 HTTP 代理服务器
const server = http.createServer((req, res) => {
  // 健康检查端点（GET / 或 GET /health）
  if (req.method === "GET" && (req.url === "/" || req.url === "/health")) {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok", models: MODEL_MAP }));
    return;
  }

  // CORS 预检请求处理
  if (req.method === "OPTIONS") {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    });
    res.end();
    return;
  }

  // 接收客户端请求体
  let body = [];
  req.on("data", (chunk) => body.push(chunk));
  req.on("end", () => {
    body = Buffer.concat(body);
    let bodyStr = body.toString();

    try {
      const parsed = JSON.parse(bodyStr);

      // 将 Claude 模型名翻译为 DeepSeek 模型名
      if (parsed.model && MODEL_MAP[parsed.model]) {
        parsed.model = MODEL_MAP[parsed.model];
      }

      // DeepSeek V4 默认将所有 token 用于 thinking，
      // 必须显式禁用 thinking 才能获得正常的文本输出
      if (!parsed.thinking) {
        parsed.thinking = { type: "disabled" };
      }

      bodyStr = JSON.stringify(parsed);
    } catch (e) {
      // JSON 解析失败时，用正则替换模型名称（兜底方案）
      for (const [from, to] of Object.entries(MODEL_MAP)) {
        bodyStr = bodyStr.replace(new RegExp(from, "g"), to);
      }
    }

    // 清理并重建转发请求头
    const fwdHeaders = { ...req.headers };
    delete fwdHeaders["content-length"];
    delete fwdHeaders["host"];
    delete fwdHeaders["authorization"];
    fwdHeaders["authorization"] = `Bearer ${API_KEY}`;
    fwdHeaders["host"] = DEEPSEEK_HOST;

    // 构建转发到 DeepSeek 的请求选项
    const options = {
      hostname: DEEPSEEK_HOST,
      port: 443,
      path: DEEPSEEK_PATH + (req.url?.replace("/v1", "") || "/v1/messages"),
      method: req.method,
      headers: fwdHeaders,
    };

    // 发送请求到上游 DeepSeek API
    const proxyReq = https.request(options, (proxyRes) => {
      // 将上游响应原样返回给客户端
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });

    // 上游请求错误处理
    proxyReq.on("error", (e) => {
      console.error("[proxy] 上游错误:", e.message);
      res.writeHead(502);
      res.end(JSON.stringify({ error: e.message }));
    });

    // 上游请求超时处理（2 分钟）
    proxyReq.setTimeout(120000, () => {
      proxyReq.destroy();
      res.writeHead(504);
      res.end(JSON.stringify({ error: "Upstream timeout" }));
    });

    proxyReq.write(bodyStr);
    proxyReq.end();
  });
});

// 服务端错误处理
server.on("error", (e) => {
  console.error("[proxy] 服务错误:", e.message);
  if (e.code === "EADDRINUSE") {
    console.error("[proxy] 端口 3200 已被占用");
    process.exit(1);
  }
});

// 启动代理，仅监听本地回环地址
server.listen(PORT, "127.0.0.1", () => {
  console.log(`[proxy] DeepSeek 代理就绪: http://127.0.0.1:${PORT}`);
  console.log(`[proxy] 所有请求已自动注入 thinking=disabled`);
  if (process.send) process.send("ready");
});
