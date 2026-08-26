import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { createProxyMiddleware } from "http-proxy-middleware";

async function startServer() {
  const app = express();
  // 注意：3000 位于 Windows Hyper-V 端口排除范围（2948-3047），绑定会被拒绝（EACCES），故使用 5173
  const PORT = 5173;
  // 用 127.0.0.1 而非 localhost：Node 24 将 localhost 优先解析为 IPv6 ::1，而后端 uvicorn 仅监听 IPv4
  const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

  app.use(express.json());

  // 统一访问主机名为 localhost：将 127.0.0.1 的请求 302 重定向到 localhost（保留路径/查询串）。
  // 原因：http://localhost:5173 与 http://127.0.0.1:5173 是两个不同的 origin，
  // localStorage 与 Cookie 互相隔离，混用会导致登录态、页面显示不一致。
  app.use((req, res, next) => {
    const host = req.headers.host || "";
    if (host.startsWith("127.0.0.1")) {
      return res.redirect(302, `http://localhost:${PORT}${req.originalUrl || "/"}`);
    }
    next();
  });

  // Health check
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", timestamp: new Date().toISOString() });
  });

  // ===== API Proxy Layer =====
  // Forward /api/* requests (excluding locally-handled /api/health) to the
  // Python FastAPI backend. /api/ai/* 亦全部转发，由后端功能开关统一控制。
  // Registered BEFORE Vite middleware so SPA fallback never swallows real API calls.
  const restProxy = createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathFilter: (proxyPath: string) => {
      // Only proxy requests under /api/ that are NOT handled locally
      if (!proxyPath.startsWith("/api/")) return false;
      if (proxyPath.startsWith("/api/health")) return false;
      return true;
    },
    on: {
      error: (err: Error) => {
        console.error("[Proxy Error]", err.message);
      },
      // express.json() 已消费请求体流，必须重建 body 再转发，否则 POST 请求会挂起超时
      proxyReq: (proxyReq: any, req: any) => {
        if (req.body && typeof req.body === "object" && Object.keys(req.body).length > 0) {
          const bodyData = JSON.stringify(req.body);
          proxyReq.setHeader("Content-Type", "application/json");
          proxyReq.setHeader("Content-Length", Buffer.byteLength(bodyData));
          proxyReq.write(bodyData);
          proxyReq.end();
        }
      },
    },
  });
  app.use(restProxy);

  // WebSocket proxy: forward /ws upgrades to the Python backend
  const wsProxy = createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    ws: true,
  });
  app.use("/ws", wsProxy);

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*all', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  // 不指定 host（Node 默认监听 :: 双栈，IPv4/IPv6 均可达）：
  // Windows 上 localhost 优先解析为 ::1，若只绑 0.0.0.0（IPv4），
  // 浏览器的 fetch/WebSocket 会连 ::1 失败报 ERR_CONNECTION_REFUSED（页面导航有 happy-eyeballs 回退故能加载）。
  const server = app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT} (IPv4+IPv6)`);
    console.log(`API proxy target: ${BACKEND_URL}`);
  });

  // Forward WebSocket upgrade requests for /ws to the backend
  server.on("upgrade", (req, socket, head) => {
    if (req.url && req.url.startsWith("/ws") && wsProxy.upgrade) {
      // Cast socket: Node's upgrade event provides Duplex, wsProxy.upgrade expects net.Socket
      wsProxy.upgrade(req, socket as any, head);
    }
  });
}

startServer();
