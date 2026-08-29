import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowRight, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { api } from '../services/api.ts';
import type { SliderCaptcha as SliderCaptchaData } from '../types.ts';

interface SliderCaptchaProps {
  /** 验证通过回调，拿到一次性票据后由调用方去请求发送验证码 */
  onSuccess: (ticket: string) => void;
  onClose: () => void;
}

/** 拖动轨迹点：[距开始毫秒数, x 位移, y 位移] */
type TrackPoint = [number, number, number];

const HANDLE_WIDTH = 40;

const SliderCaptcha: React.FC<SliderCaptchaProps> = ({ onSuccess, onClose }) => {
  const [data, setData] = useState<SliderCaptchaData | null>(null);
  const [offsetX, setOffsetX] = useState(0);
  const [dragging, setDragging] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');

  const trackRef = useRef<TrackPoint[]>([]);
  const startAtRef = useRef(0);
  const startClientXRef = useRef(0);
  const startOffsetRef = useRef(0);

  const load = useCallback(async () => {
    setError('');
    setOffsetX(0);
    trackRef.current = [];
    try {
      const res = await api.auth.captchaSlider();
      if (res.code === 0 && res.data) {
        setData(res.data);
      } else {
        setError(res.message || '获取验证失败，请重试');
      }
    } catch {
      setError('无法获取验证，请检查网络后重试');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const maxOffset = data ? Math.max(data.width - data.slider_size, 1) : 1;
  const barWidth = data?.width ?? 320;
  // 拖动条可用行程与滑块可移动范围成比例，保证视觉位置与提交值一致
  const dragRange = Math.max(barWidth - HANDLE_WIDTH, 1);
  const handleLeft = (offsetX / maxOffset) * dragRange;

  const clamp = (value: number) => Math.max(0, Math.min(value, maxOffset));

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!data || verifying) return;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    setDragging(true);
    setError('');
    startAtRef.current = Date.now();
    startClientXRef.current = e.clientX;
    startOffsetRef.current = offsetX;
    trackRef.current = [[0, offsetX, 0]];
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging) return;
    // 拖动条像素 → 滑块位移 的比例换算
    const ratio = dragRange / maxOffset;
    const next = clamp(startOffsetRef.current + (e.clientX - startClientXRef.current) / ratio);
    setOffsetX(next);
    trackRef.current.push([Date.now() - startAtRef.current, next, 0]);
  };

  const handlePointerUp = async () => {
    if (!dragging || !data) return;
    setDragging(false);

    const elapsed = Date.now() - startAtRef.current;
    // 轨迹采集过少时补一个终点，避免后端直接判为脚本
    const track =
      trackRef.current.length >= 2
        ? trackRef.current
        : ([
            [0, 0, 0],
            [elapsed, offsetX, 0],
          ] as TrackPoint[]);

    setVerifying(true);
    try {
      const res = await api.auth.captchaVerify(data.token, offsetX, track, elapsed);
      if (res.code === 0 && res.data?.ticket) {
        onSuccess(res.data.ticket);
      } else {
        setError(res.message || '验证未通过，请重试');
        // 令牌一次性：失败后必须重新获取，不能原地再拖
        await load();
      }
    } catch {
      setError('验证失败，请重试');
      await load();
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-sm space-y-4 rounded-2xl bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
            <ShieldCheck className="h-4 w-4 text-indigo-600" />
            安全验证
          </div>
          <div className="flex items-center gap-1">
            <button type="button" onClick={load} title="刷新验证" className="p-1">
              <RefreshCw className="h-4 w-4 text-slate-400 hover:text-indigo-600" />
            </button>
            <button type="button" onClick={onClose} title="关闭" className="p-1">
              <X className="h-4 w-4 text-slate-400 hover:text-slate-700" />
            </button>
          </div>
        </div>

        {/* 拼图画布 */}
        <div
          className="relative select-none overflow-hidden rounded-xl bg-slate-100"
          style={{ width: barWidth, height: data?.height ?? 160 }}
        >
          {data ? (
            <>
              <img
                src={data.background}
                alt="验证背景"
                draggable={false}
                style={{ width: data.width, height: data.height }}
              />
              <img
                src={data.slider}
                alt="拼图块"
                draggable={false}
                className="absolute"
                style={{
                  left: offsetX,
                  top: data.y,
                  width: data.slider_size,
                  height: data.slider_size,
                }}
              />
            </>
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-slate-400">
              {error || '加载中…'}
            </div>
          )}
        </div>

        {/* 拖动条 */}
        <div
          className={`relative h-11 touch-none select-none rounded-xl border transition-colors ${
            error ? 'border-rose-300 bg-rose-50' : 'border-slate-200 bg-slate-50'
          }`}
          style={{ width: barWidth }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-xs text-slate-400">
            {verifying ? '验证中…' : '按住滑块，拖动到缺口位置'}
          </div>
          <div
            className="pointer-events-none absolute top-0 left-0 h-full rounded-l-xl bg-indigo-100"
            style={{ width: handleLeft + HANDLE_WIDTH / 2 }}
          />
          <div
            className={`absolute top-0 flex h-full items-center justify-center rounded-xl border bg-white shadow-sm ${
              dragging ? 'cursor-grabbing border-indigo-400' : 'cursor-grab border-slate-200'
            }`}
            style={{ left: handleLeft, width: HANDLE_WIDTH }}
          >
            <ArrowRight className="h-4 w-4 text-indigo-600" />
          </div>
        </div>

        {error && <p className="text-xs text-rose-600">{error}</p>}
        <p className="text-[11px] leading-relaxed text-slate-400">
          完成验证后才会发送验证码，可有效防止恶意刷取。
        </p>
      </div>
    </div>
  );
};

export default SliderCaptcha;
