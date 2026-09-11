var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// server.ts
var import_express = __toESM(require("express"), 1);
var import_path = __toESM(require("path"), 1);
var import_vite = require("vite");
var import_http_proxy_middleware = require("http-proxy-middleware");
async function startServer() {
  const app = (0, import_express.default)();
  const PORT = 5173;
  const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";
  app.use(import_express.default.json());
  app.use((req, res, next) => {
    const host = req.headers.host || "";
    if (host.startsWith("127.0.0.1")) {
      return res.redirect(302, `http://localhost:${PORT}${req.originalUrl || "/"}`);
    }
    next();
  });
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", timestamp: (/* @__PURE__ */ new Date()).toISOString() });
  });
  const restProxy = (0, import_http_proxy_middleware.createProxyMiddleware)({
    target: BACKEND_URL,
    changeOrigin: true,
    pathFilter: (proxyPath) => {
      if (!proxyPath.startsWith("/api/")) return false;
      if (proxyPath.startsWith("/api/health")) return false;
      return true;
    },
    on: {
      error: (err) => {
        console.error("[Proxy Error]", err.message);
      },
      // express.json() 已消费请求体流，必须重建 body 再转发，否则 POST 请求会挂起超时
      proxyReq: (proxyReq, req) => {
        if (req.body && typeof req.body === "object" && Object.keys(req.body).length > 0) {
          const bodyData = JSON.stringify(req.body);
          proxyReq.setHeader("Content-Type", "application/json");
          proxyReq.setHeader("Content-Length", Buffer.byteLength(bodyData));
          proxyReq.write(bodyData);
          proxyReq.end();
        }
      }
    }
  });
  app.use(restProxy);
  const wsProxy = (0, import_http_proxy_middleware.createProxyMiddleware)({
    target: BACKEND_URL,
    changeOrigin: true,
    ws: true
  });
  app.use("/ws", wsProxy);
  if (process.env.NODE_ENV !== "production") {
    const vite = await (0, import_vite.createServer)({
      server: { middlewareMode: true },
      appType: "spa"
    });
    app.use(vite.middlewares);
  } else {
    const distPath = import_path.default.join(process.cwd(), "dist");
    app.use(import_express.default.static(distPath));
    app.get("*all", (req, res) => {
      res.sendFile(import_path.default.join(distPath, "index.html"));
    });
  }
  const server = app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT} (IPv4+IPv6)`);
    console.log(`API proxy target: ${BACKEND_URL}`);
  });
  server.on("upgrade", (req, socket, head) => {
    if (req.url && req.url.startsWith("/ws") && wsProxy.upgrade) {
      wsProxy.upgrade(req, socket, head);
    }
  });
}
startServer();
//# sourceMappingURL=server.cjs.map
