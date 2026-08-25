import express from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI, Type } from "@google/genai";
import { createProxyMiddleware } from "http-proxy-middleware";

async function startServer() {
  const app = express();
  // 注意：3000 位于 Windows Hyper-V 端口排除范围（2948-3047），绑定会被拒绝（EACCES），故使用 5173
  const PORT = 5173;
  // 用 127.0.0.1 而非 localhost：Node 24 将 localhost 优先解析为 IPv6 ::1，而后端 uvicorn 仅监听 IPv4
  const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

  app.use(express.json());

  // Shared Gemini client utility
  const getAI = () => {
    const apiKey = process.env.GEMINI_API_KEY || process.env.API_KEY || "";
    return new GoogleGenAI({
      apiKey: apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        }
      }
    });
  };

  // Resilient multi-model executor with automatic fallback on 503/429/high demand
  const generateWithFallback = async (
    params: { contents: any; config?: any },
    preferredModels: string[] = ['gemini-2.5-flash', 'gemini-3.1-flash-lite', 'gemini-flash-latest']
  ) => {
    const ai = getAI();
    let lastError: any = null;

    for (const model of preferredModels) {
      try {
        const response = await ai.models.generateContent({
          model,
          contents: params.contents,
          config: params.config,
        });
        if (response && response.text) {
          return response;
        }
      } catch (err: any) {
        lastError = err;
        // Continue to the next fallback model in the pipeline
        continue;
      }
    }
    throw lastError || new Error("All Gemini models temporarily unavailable.");
  };

  // Health check
  app.get("/api/health", (req, res) => {
    res.json({ status: "ok", timestamp: new Date().toISOString() });
  });

  // Curated fallback insights by topic
  const defaultInsights: Record<string, string[]> = {
    '考试周高效复习技巧': [
      '用番茄钟分段复习，重点攻克历年真题与错题集，保持充足睡眠！',
      '梳理思维导图搭建知识框架，配合碎片时间回顾高频考点。',
      '找安静研讨室结伴自习，互相抽背公式与核心概念，事半功倍！'
    ],
    '一食堂今日招牌美食推荐': [
      '学一食堂兰州拉面与金汤酸菜鱼人气正旺，错峰前往少排队！',
      '二楼广式烧腊档双拼饭香气扑鼻，配免费例汤营养又划算。',
      '清真餐厅新疆大盘鸡拌面现炒出锅，分量十足适合与室友共享！'
    ],
    '大三找实习与竞赛组队策略': [
      '早建简历突出项目亮点，在搭子广场找到技术互补的靠谱队友！',
      '关注校招就业公众号与学院通告，多参加校内答辩积累实战经验。',
      '明确分工与里程碑节点，竞赛准备重在定期复盘与论文精修。'
    ],
    '二手闲置避坑与面交安全': [
      '校内交易优先选择图书馆或宿管大厅面交，当场验机验物更安心！',
      '描述诚恳成色清晰，保留交易聊天记录，让校园闲置流转更温暖。',
      '贵重数码建议查看电池健康与购买凭证，支持校友友好小刀。'
    ]
  };

  // 1. Campus smart daily insight
  app.post("/api/ai/insights", async (req, res) => {
    const { topic } = req.body || {};
    const selectedTopic = topic || '大学日常生活';
    try {
      const response = await generateWithFallback({
        contents: `围绕“${selectedTopic}”，为在校大学生写一句不超过35字的温暖、积极、实用的今日校园生活与学习贴心指南。不需要任何标题，直接输出一句话。`,
      });
      res.json({
        code: 0,
        text: response.text?.trim() || "今日校园充满活力，记得劳逸结合，享受美好的大学时光！"
      });
    } catch (error: any) {
      console.warn("Using curated smart insight fallback for topic:", selectedTopic);
      const list = defaultInsights[selectedTopic] || defaultInsights['考试周高效复习技巧'];
      const fallbackText = list[Math.floor(Math.random() * list.length)] || "今日校园充满活力，记得劳逸结合，享受美好的大学时光！";
      res.json({
        code: 0,
        text: fallbackText,
        fallback: true
      });
    }
  });

  // 2. Market Item description generation
  app.post("/api/ai/item-description", async (req, res) => {
    const { title, category } = req.body || {};
    const itemTitle = title || '二手闲置物品';
    try {
      const response = await generateWithFallback({
        contents: `请为在大学校园二手市集出售的物品【${itemTitle}】（分类：${category || '日常用品'}）生成一段诚恳、详细且吸引人的转让文案，包含成色描述、使用体验、为何转让、适合哪些专业的学弟学妹、以及校内当面验货交易的说明（100字左右）。`,
      });
      res.json({
        code: 0,
        text: response.text?.trim() || `【${itemTitle}】成色完好，功能全部正常。因毕业/闲置现优惠转让给校内学弟学妹，支持校内图书馆或宿舍楼下当面验货交易！`
      });
    } catch (error: any) {
      console.warn("Using default item description fallback for:", itemTitle);
      res.json({
        code: 0,
        text: `【${itemTitle}】成色完好，功能全部正常。平时非常爱惜无任何暗病，配件齐全。因升级/毕业闲置现低价转让给校内同学，支持图书馆或宿舍楼下当面验货交易！`,
        fallback: true
      });
    }
  });

  // 3. Summarize course reviews
  app.post("/api/ai/course-summary", async (req, res) => {
    const { reviewTexts } = req.body || {};
    const texts: string[] = Array.isArray(reviewTexts) ? reviewTexts : [];
    if (texts.length === 0) {
      return res.json({
        code: 0,
        text: "暂无足够的真实学生评价数据进行深度画像提炼。"
      });
    }
    try {
      const prompt = `根据以下学生对本门课程的真实评价，提炼出一份精炼客观的选课总结（包括：课程难易度、作业考核要求、老师讲课风格、给分情况与期末避坑建议，控制在120字以内）：\n${texts.join('\n- ')}`;
      const response = await generateWithFallback({
        contents: prompt,
      });
      res.json({
        code: 0,
        text: response.text?.trim() || "综合评分良好，老师讲课通俗易懂，平时作业量适中，期末注重考查基础知识与课堂互动。"
      });
    } catch (error: any) {
      console.warn("Using default course summary fallback");
      res.json({
        code: 0,
        text: "综合评价良好：授课条理清晰重点突出，平时编程/研讨作业量适中，给分客观公允，期末考查覆盖课堂核心要点，建议认真参与课堂互动。",
        fallback: true
      });
    }
  });

  // 4. Categorize campus post
  app.post("/api/ai/categorize", async (req, res) => {
    const { content } = req.body || {};
    try {
      const response = await generateWithFallback({
        contents: `Categorize this campus post: "${content}"`,
        config: {
          responseMimeType: "application/json",
          responseSchema: {
            type: Type.OBJECT,
            properties: {
              category: { type: Type.STRING, description: "Market, Course, Canteen, Teammate, Share, Job" },
              isSafe: { type: Type.BOOLEAN, description: "Whether the content is appropriate for campus" },
              summary: { type: Type.STRING }
            },
            required: ["category", "isSafe", "summary"]
          }
        }
      });
      const parsed = JSON.parse(response.text || '{}');
      res.json({ code: 0, data: parsed });
    } catch (error: any) {
      console.warn("Using categorize fallback");
      res.json({
        code: 0,
        data: { category: 'General', isSafe: true, summary: content || '' },
        fallback: true
      });
    }
  });

  // ===== API Proxy Layer =====
  // Forward /api/* requests (excluding locally-handled /api/ai/* and /api/health)
  // to the Python FastAPI backend. Registered AFTER local AI/health routes,
  // BEFORE Vite middleware so SPA fallback never swallows real API calls.
  const restProxy = createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    pathFilter: (proxyPath: string) => {
      // Only proxy requests under /api/ that are NOT handled locally
      if (!proxyPath.startsWith("/api/")) return false;
      if (proxyPath.startsWith("/api/ai/")) return false;
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

  const server = app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://0.0.0.0:${PORT}`);
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
