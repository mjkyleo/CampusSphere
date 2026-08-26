/**
 * AI 智能助手客户端服务。
 *
 * 说明：
 * - 后端提供 /api/ai/* 接口（Gemini），功能开关由管理员在后台控制；
 * - 本模块不再内置任何硬编码演示文案：开关关闭或接口异常时直接抛出错误，
 *   由调用方页面根据 /api/ai/status 决定是否渲染 AI 入口，避免"假数据"误导；
 * - 状态查询结果为模块级缓存（同一页面会话内最多请求一次）。
 */

import type { AiStatusOut } from '../types.ts';

interface ApiEnvelope<T> {
  code: number;
  message: string;
  data?: T;
}

let statusCache: AiStatusOut | null = null;

/** 查询 AI 功能开关状态（公开端点，无需登录）。失败时按"未开启"处理。 */
export async function getAiStatus(): Promise<AiStatusOut> {
  if (statusCache) return statusCache;
  try {
    const res = await fetch('/api/ai/status');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = (await res.json()) as ApiEnvelope<AiStatusOut>;
    if (body.code === 0 && body.data) {
      statusCache = body.data;
      return statusCache;
    }
    throw new Error(body.message || 'status error');
  } catch {
    // 网络/服务异常一律视为不可用，前端隐藏 AI 入口
    statusCache = { enabled: false, available: false, message: 'AI 服务暂不可用' };
    return statusCache;
  }
}

/** 供管理后台修改开关后使本地缓存失效（可选调用，不强制）。 */
export function invalidateAiStatusCache(): void {
  statusCache = null;
}

async function post<T>(endpoint: string, body: unknown): Promise<T> {
  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  let payload: ApiEnvelope<T>;
  try {
    payload = (await res.json()) as ApiEnvelope<T>;
  } catch {
    throw new Error('AI 服务响应异常，请稍后重试');
  }
  if (!res.ok || payload.code !== 0) {
    throw new Error(payload.message || 'AI 功能暂未开放，敬请期待');
  }
  if (payload.data === undefined || payload.data === null) {
    throw new Error('AI 服务返回异常，请稍后重试');
  }
  return payload.data;
}

/** 首页：今日校园智能灵感。 */
export async function getSmartCampusInsights(topic: string): Promise<string> {
  const data = await post<{ text: string }>('/api/ai/insights', { topic });
  return data.text;
}

/** 闲置发布页：AI 智能润色物品描述。 */
export async function generateItemDescription(title: string, category: string): Promise<string> {
  const data = await post<{ text: string }>('/api/ai/item-description', { title, category });
  return data.text;
}

/** 课程详情页：AI 汇总提炼课程评价。 */
export async function summarizeCourseReviews(reviewTexts: string[]): Promise<string> {
  const data = await post<{ text: string }>('/api/ai/course-summary', { reviewTexts });
  return data.text;
}

/** 内容自动分类与安全预审（发帖场景预留）。 */
export async function categorizePost(
  content: string
): Promise<{ category: string; isSafe: boolean; summary: string }> {
  const data = await post<{ category: string; isSafe: boolean; summary: string }>(
    '/api/ai/categorize',
    { content }
  );
  return data;
}
