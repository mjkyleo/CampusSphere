/**
 * AI 智能助手统一客户端（合并原 api.ai.* 与 geminiService.*）。
 *
 * 设计要点：
 * - **唯一入口**：所有页面只依赖本模块，避免两套客户端各自缓存状态导致不一致；
 * - **能力级 gating**：`isCapabilityAvailable(status, name)` 决定单个 AI 入口是否渲染，
 *   AI 未配置 / 服务不可用时一律返回 false，前端自动隐藏入口，主流程零阻塞；
 * - **问候永不失败**：`getGreeting()` 在开关关闭、未登录、网络异常时降级到
 *   `localGreeting()`，首页照常展示一句问候，只是不显示「AI」角标。
 */

import { api } from './api.ts';
import type {
  AiConfig, AiConfigUpdate, AiFeatureConfig, AiGreeting, AiStatusOut
} from '../types.ts';

/** 状态缓存（同一会话内最多请求一次，管理端改配置后调用 invalidateAiStatusCache 失效） */
let statusCache: AiStatusOut | null = null;
let statusInflight: Promise<AiStatusOut> | null = null;

const UNAVAILABLE: AiStatusOut = {
  enabled: false,
  available: false,
  message: 'AI 服务暂不可用'
};

export async function getAiStatus(force = false): Promise<AiStatusOut> {
  if (!force && statusCache) return statusCache;
  if (!force && statusInflight) return statusInflight;

  statusInflight = (async () => {
    try {
      const res = await api.ai.status();
      const next = res?.code === 0 && res.data ? res.data : UNAVAILABLE;
      statusCache = next;
      return next;
    } catch {
      statusCache = UNAVAILABLE;
      return statusCache;
    } finally {
      statusInflight = null;
    }
  })();
  return statusInflight;
}

/** 管理后台修改开关后调用，使本地缓存立即失效。 */
export function invalidateAiStatusCache(): void {
  statusCache = null;
  statusInflight = null;
}

/** 单个能力是否可渲染（能力缺失时按全局 available 兜底）。 */
export function isCapabilityAvailable(
  status: AiStatusOut | null,
  name: string
): boolean {
  if (!status) return false;
  const cap = status.capabilities?.[name];
  if (cap) return !!cap.available;
  return !!status.available;
}

// ------------------------------------------------------------------
// 首页问候（含本地降级）
// ------------------------------------------------------------------

const LOCAL_POOL: Record<string, string[]> = {
  energetic: [
    '状态在线，今天适合啃那块最硬的骨头。',
    '别浪费这股劲，先做那件你一直拖着的事。',
    '满格电量，也记得中途补个水。',
    '今天适合开新坑：那门想选的课、那个想报的比赛。',
    '好状态是用来做难事的，不是用来刷手机的。'
  ],
  steady: [
    '稳一点也没关系，进度条在动就行。',
    '不急，今天完成一件小事也算赢。',
    '把大任务切成三块，做完一块夸自己一次。',
    '你不需要每天都很燃，持续就够了。',
    '今天把那件拖了三天的事清掉，就是赢。'
  ],
  tired: [
    '先喝口水，你已经扛了很久了。',
    '累了就歇会儿，进度条不会因此归零。',
    '今天允许自己只做到六十分。',
    '疲惫是信号不是缺点，听它的。',
    '休息不是浪费时间，是给明天充值。'
  ],
  sprint: [
    '冲刺阶段，别和别人比进度。',
    '把手机扣下，专注两小时，胜过焦虑一整天。',
    '最后这段路，拼的是稳，不是快。',
    '焦虑说明你在乎，把它换成一道题。',
    '今天的专注，就是考场上的底气。'
  ],
  generic: [
    '今天也请多关照。',
    '校园里总有小事值得期待。',
    '今天也要好好吃饭。',
    '愿今天有一件小事让你开心。'
  ]
};

const PERIOD_LABEL: Record<string, string> = {
  early: '清晨', morning: '上午', noon: '午后', evening: '傍晚', night: '夜里'
};
const PERIOD_EMOJI: Record<string, string> = {
  early: '🌅', morning: '☀️', noon: '🌤️', evening: '🌆', night: '🌙'
};

export function currentPeriod(): string {
  const h = new Date().getHours();
  if (h >= 5 && h < 9) return 'early';
  if (h >= 9 && h < 12) return 'morning';
  if (h >= 12 && h < 18) return 'noon';
  if (h >= 18 && h < 22) return 'evening';
  return 'night';
}

/** 本地模板问候：零网络、零阻塞，按日期种子保证每次启动不同。 */
export function localGreeting(mood = '', seed = Date.now()): AiGreeting {
  const period = currentPeriod();
  const pool = LOCAL_POOL[mood] || LOCAL_POOL.generic;
  const idx = Math.abs(seed) % pool.length;
  return {
    text: `${PERIOD_LABEL[period]}好，${pool[idx]}`,
    emoji: PERIOD_EMOJI[period],
    source: 'fallback',
    period,
    mood,
    focus: '',
    attempt: 0
  };
}

export interface GreetingOptions {
  mood?: string;
  focus?: string;
  clientSeed?: string;
  regenerate?: boolean;
}

/**
 * 获取每日问候：**永不抛错**。
 * 后端不可用 / 未登录 / 网络异常 → 降级到本地模板。
 */
export async function getGreeting(opts: GreetingOptions = {}): Promise<AiGreeting> {
  const status = await getAiStatus();
  if (!isCapabilityAvailable(status, 'greeting')) {
    return localGreeting(opts.mood, hashSeed(opts));
  }
  try {
    const res = await api.ai.greeting({
      mood: opts.mood || '',
      focus: opts.focus || '',
      clientSeed: opts.clientSeed || '',
      regenerate: !!opts.regenerate
    });
    if (res?.code === 0 && res.data?.text) return res.data;
  } catch {
    // 落到本地模板
  }
  return localGreeting(opts.mood, hashSeed(opts));
}

function hashSeed(opts: GreetingOptions): number {
  const raw = `${opts.mood || ''}:${opts.focus || ''}:${opts.clientSeed || ''}:${Date.now()}`;
  let h = 0;
  for (let i = 0; i < raw.length; i++) {
    h = (h * 31 + raw.charCodeAt(i)) | 0;
  }
  return h;
}

// ------------------------------------------------------------------
// 生成类能力（不可降级：失败即抛，由页面提示，绝不展示假数据）
// ------------------------------------------------------------------

async function unwrap<T>(res: { code: number; message?: string; data?: T }): Promise<T> {
  if (!res || res.code !== 0 || res.data === undefined || res.data === null) {
    throw new Error(res?.message || 'AI 功能暂未开放，敬请期待');
  }
  return res.data;
}

export async function getInsights(topic: string): Promise<string> {
  const res = await api.ai.getInsights(topic);
  const data = await unwrap<{ text: string }>(res);
  return data.text;
}

// 兼容历史命名：HomePage 仍引用 getSmartCampusInsights
export const getSmartCampusInsights = getInsights;

export async function generateItemDescription(title: string, category: string): Promise<string> {
  const res = await api.ai.generateItemDescription(title, category);
  const data = await unwrap<{ text: string }>(res);
  return data.text;
}

export async function summarizeCourseReviews(reviewTexts: string[]): Promise<string> {
  const res = await api.ai.summarizeCourseReviews(reviewTexts);
  const data = await unwrap<{ text: string }>(res);
  return data.text;
}

export async function categorizePost(
  content: string
): Promise<{ category: string; isSafe: boolean; summary: string; source: string }> {
  const res = await api.ai.categorizePost(content);
  return unwrap(res);
}

// ------------------------------------------------------------------
// 管理端配置
// ------------------------------------------------------------------

export const getAiConfig = (): Promise<AiConfig> =>
  api.ai.getConfig().then((r) => unwrap<AiConfig>(r));

export const updateAiConfig = (config: AiConfigUpdate): Promise<AiFeatureConfig> =>
  api.ai.updateConfig(config).then((r) => unwrap<AiFeatureConfig>(r));
