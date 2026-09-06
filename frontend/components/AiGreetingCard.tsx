import React, { useState, useEffect, useCallback } from 'react';
import { Sparkles, RefreshCw } from 'lucide-react';
import { getGreeting } from '../services/aiService.ts';
import type { AiGreeting } from '../types.ts';

/**
 * 首页「每日问候 · 微采集」卡片。
 *
 * 交互：每次启动先用一次性 seed 取一条问候；若今天还没采集过，则展示一张
 * 轻量采集卡（状态 + 今日重点），用户点选后重新生成一条更贴合的问候。
 *
 * 降级：AI 未配置 / 未登录 / 网络异常时 `getGreeting()` 返回本地模板
 * （`source='fallback'`），此时**照常渲染卡片**，只是不显示「AI」角标——
 * 首页永不因 AI 而空白或报错。
 */

// 每次页面启动重新生成，是「每次启动问候不同」的关键输入之一
const SESSION_SEED = `${Date.now()}-${Math.random().toString(36).slice(2)}`;

const KEY_DATE = 'cs_greeting_date';
const KEY_MOOD = 'cs_greeting_mood';
const KEY_FOCUS = 'cs_greeting_focus';

const MOODS = [
  { key: 'energetic', label: '元气满满', emoji: '⚡' },
  { key: 'steady', label: '稳中求进', emoji: '🌱' },
  { key: 'tired', label: '有点疲惫', emoji: '🫖' },
  { key: 'sprint', label: '冲刺备战', emoji: '🎯' }
];

const FOCUS = [
  { key: 'study', label: '课业' },
  { key: 'contest', label: '竞赛' },
  { key: 'social', label: '社交' },
  { key: 'relax', label: '摸鱼' }
];

const today = () => new Date().toDateString();

const AiGreetingCard: React.FC = () => {
  const [greeting, setGreeting] = useState<AiGreeting | null>(null);
  const [loading, setLoading] = useState(true);
  const [collected, setCollected] = useState(true);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [mood, setMood] = useState<string>('');
  const [focus, setFocus] = useState<string>('');

  const load = useCallback(async (m: string, f: string, regen = false) => {
    setLoading(true);
    try {
      const g = await getGreeting({
        mood: m, focus: f, clientSeed: SESSION_SEED, regenerate: regen
      });
      setGreeting(g);
    } catch {
      setGreeting(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const isToday = localStorage.getItem(KEY_DATE) === today();
    const m = isToday ? localStorage.getItem(KEY_MOOD) || '' : '';
    const f = isToday ? localStorage.getItem(KEY_FOCUS) || '' : '';
    setMood(m);
    setFocus(f);
    setCollected(isToday);
    setPickerOpen(!isToday);
    load(m, f);
  }, [load]);

  const submitCollection = () => {
    localStorage.setItem(KEY_DATE, today());
    localStorage.setItem(KEY_MOOD, mood);
    localStorage.setItem(KEY_FOCUS, focus);
    setCollected(true);
    setPickerOpen(false);
    load(mood, focus);
  };

  const isAi = greeting?.source === 'llm';

  return (
    <div className="bg-white/5 border border-white/10 backdrop-blur-xs rounded-2xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <span className="text-xl leading-none mt-0.5" aria-hidden>
            {greeting?.emoji || '✨'}
          </span>
          <div className="min-w-0">
            {loading && !greeting ? (
              <span className="text-sm text-slate-400 animate-pulse">正在准备今日问候...</span>
            ) : (
              <p className="text-sm md:text-base text-slate-100 leading-relaxed">
                {greeting?.text || '欢迎回来，今天也请多关照。'}
              </p>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => load(mood, focus, true)}
          disabled={loading}
          title="换一句"
          className="shrink-0 p-1.5 rounded-lg text-slate-400 hover:text-indigo-300 hover:bg-white/10 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      <div className="flex items-center gap-2">
        {isAi && (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/10 text-[11px] font-medium text-indigo-200">
            <Sparkles className="w-3 h-3 text-indigo-400" />
            AI 生成
          </span>
        )}
        {!pickerOpen && (
          <button
            type="button"
            onClick={() => setPickerOpen(true)}
            className="text-[11px] text-indigo-300 hover:text-indigo-200 underline-offset-2 hover:underline"
          >
            换个更懂我的问候
          </button>
        )}
      </div>

      {pickerOpen && (
        <div className="space-y-2.5 pt-1 border-t border-white/10">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-slate-400 mr-1">今天状态</span>
            {MOODS.map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => setMood(m.key)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${
                  mood === m.key
                    ? 'bg-indigo-500/30 border-indigo-400/50 text-white'
                    : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                }`}
              >
                {m.emoji} {m.label}
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-slate-400 mr-1">今日重点</span>
            {FOCUS.map((f) => (
              <button
                key={f.key}
                type="button"
                onClick={() => setFocus(f.key)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${
                  focus === f.key
                    ? 'bg-indigo-500/30 border-indigo-400/50 text-white'
                    : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={submitCollection}
            disabled={loading}
            className="px-3 py-1.5 rounded-xl bg-indigo-500/90 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors disabled:opacity-50"
          >
            就按这个来
          </button>
        </div>
      )}
    </div>
  );
};

export default AiGreetingCard;
