/**
 * 飞书 <-> Claude Code Bot (最终版)
 *
 * 僵尸进程防护:
 *   1. tree-kill 可靠杀子进程 (MSYS2兼容)
 *   2. 启动前全杀旧僵尸 (wmic cleanup)
 *   3. --timeout 限时运行 (官方子进程模式,无需stdin)
 *   4. SIGINT/SIGTERM 触发 tree-kill 清理
 *
 * 消息处理:
 *   两层去重 (message_id Set + create_time 5min过期)
 *   单实例 PID 锁
 *   并发保护
 */
import { spawn, execSync } from "child_process";
import { existsSync, readFileSync, writeFileSync, unlinkSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";
const treeKill = createRequire(import.meta.url)("tree-kill");

const __dirname = dirname(fileURLToPath(import.meta.url));
const C = {
  claude: "E:/claude-code/node_modules/@anthropic-ai/claude-code/bin/claude.exe",
  workDir: "E:/工作AI",
  maxAge: 5 * 60 * 1000,          // 5分钟消息过期
  timeout: "300s",                  // lark-cli 每轮300秒
  maxEvents: "50",
  pidFile: resolve(__dirname, "..", "临时文件", "claude_bot.pid"),
};

// ====== 启动前: 杀光所有僵尸 lark-cli 进程 ======
function killZombies() {
  try {
    // 杀 event bus
    execSync('wmic process where "name=\'node.exe\'" get commandline,processid 2>nul | findstr "event._bus"', { timeout: 5000, stdio: "pipe" })
      .toString().match(/\d+$/gm)?.forEach(pid => {
        try { execSync(`taskkill /F /PID ${pid} 2>nul`, { timeout: 3000, stdio: "ignore" }); } catch {}
      });
    // 杀 event consume
    execSync('wmic process where "name=\'node.exe\'" get commandline,processid 2>nul | findstr "event.consume"', { timeout: 5000, stdio: "pipe" })
      .toString().match(/\d+$/gm)?.forEach(pid => {
        try { execSync(`taskkill /F /PID ${pid} 2>nul`, { timeout: 3000, stdio: "ignore" }); } catch {}
      });
    console.log("[启动] 已清理旧进程");
  } catch {}
}

killZombies();

// ====== 单实例锁 ======
if (existsSync(C.pidFile)) {
  try { process.kill(parseInt(readFileSync(C.pidFile, "utf-8")), 0); console.log("已有实例"); process.exit(0); }
  catch { try { unlinkSync(C.pidFile); } catch {} }
}
writeFileSync(C.pidFile, String(process.pid));

// ====== 状态 ======
const seen = new Set();
let busy = false;
let larkChild = null;

// ====== 调用 Claude ======
function claude(text) {
  return new Promise(r => {
    const c = spawn(C.claude, ["-p", `[飞书私聊] ${text}`, "--dangerously-skip-permissions", "--output-format", "text"], {
      cwd: C.workDir, timeout: 300000, stdio: ["ignore", "pipe", "pipe"], shell: true, windowsHide: true,
    });
    let o = ""; c.stdout.on("data", d => o += d.toString());
    c.on("close", () => r(o.trim() || null));
    c.on("error", () => r(null));
  });
}

// ====== 发送回复 ======
function reply(msgId, text) {
  const safe = text.slice(0, 4800).replace(/"/g, '\\"');
  return new Promise(r => {
    spawn("lark-cli.cmd", ["im", "+messages-reply", "--message-id", msgId, "--text", safe, "--as", "bot"], {
      timeout: 15000, stdio: "ignore", shell: true, windowsHide: true,
    }).on("close", code => r(code === 0));
  });
}

// ====== 事件处理 ======
async function handle(evt) {
  try {
    const { message_id: id, content: txt, chat_type: ct, create_time: ts } = evt;
    if (!id || !txt) return;
    if (seen.has(id)) return;
    seen.add(id); if (seen.size > 1000) seen.clear();
    if (ts && Date.now() - parseInt(ts) > C.maxAge) return;

    console.log(`[${new Date().toLocaleTimeString()}] [${ct || "p2p"}] ${txt.slice(0, 80)}`);
    if (busy) return; busy = true;
    const r = await claude(txt);
    if (r) { console.log(`  → ${r.slice(0, 100)}`); await reply(id, r); }
    busy = false;
  } catch (e) { busy = false; }
}

// ====== 事件监听 (--timeout 限时模式) ======
function start() {
  larkChild = spawn("lark-cli.cmd", [
    "event", "consume", "im.message.receive_v1",
    "--timeout", C.timeout, "--max-events", C.maxEvents, "--as", "bot",
  ], { stdio: ["ignore", "pipe", "pipe"], shell: true, windowsHide: true });

  let buf = "";
  larkChild.stdout.on("data", d => {
    buf += d.toString();
    const ls = buf.split("\n"); buf = ls.pop();
    for (const l of ls) { if (l.startsWith("{")) try { handle(JSON.parse(l)); } catch {} }
  });

  larkChild.on("close", (code) => {
    console.log(`[${new Date().toLocaleTimeString()}] 轮次结束(${code}) 3秒后重启`);
    setTimeout(start, 3000);
  });

  console.log(`[${new Date().toLocaleString()}] Bot PID:${process.pid} | tree-kill防护 | timeout=${C.timeout}`);
}

// ====== 退出时清理 ======
function cleanup() {
  console.log("[退出] 清理子进程...");
  if (larkChild) treeKill(larkChild.pid, "SIGKILL", () => {});
  try { unlinkSync(C.pidFile); } catch {}
  process.exit(0);
}
process.on("SIGINT", cleanup);
process.on("SIGTERM", cleanup);

start();
