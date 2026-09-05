import React, { useCallback, useEffect, useRef, useState } from 'react';
import { RefreshCw, ShieldCheck, X } from 'lucide-react';
import { api } from '../services/api.ts';
import type { GeetestValidate } from '../types.ts';

interface GeetestCaptchaProps {
  /** 极验后台申请的 captchaId，由 /api/auth/captcha/config 下发 */
  captchaId: string;
  /** 二次校验通过回调，拿到一次性票据后由调用方去请求发送验证码 */
  onSuccess: (ticket: string) => void;
  onClose: () => void;
}

/** 极验 gt4.js 注入的全局初始化函数与实例方法。 */
declare global {
  interface Window {
    initGeetest4?: (
      config: Record<string, unknown>,
      callback: (captcha: GeetestInstance) => void,
    ) => void;
  }
}

interface GeetestInstance {
  appendTo: (target: string | HTMLElement) => void;
  onReady: (cb: () => void) => GeetestInstance;
  onSuccess: (cb: () => void) => GeetestInstance;
  onFail: (cb: (obj: unknown) => void) => GeetestInstance;
  onError: (cb: (err: unknown) => void) => GeetestInstance;
  onClose: (cb: () => void) => GeetestInstance;
  getValidate: () => GeetestValidate | false;
  reset: () => void;
  destroy: () => void;
}

const GT4_SRC = 'https://static.geetest.com/v4/gt4.js';

// 脚本只需加载一次：多个组件实例共享同一个 Promise，避免重复插入 script 标签。
let gt4Loader: Promise<void> | null = null;

function loadGt4(): Promise<void> {
  if (gt4Loader) return gt4Loader;
  gt4Loader = new Promise<void>((resolve, reject) => {
    if (window.initGeetest4) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = GT4_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      // 清空缓存，允许用户点"刷新"时重新尝试加载
      gt4Loader = null;
      reject(new Error('gt4.js load failed'));
    };
    document.head.appendChild(script);
  });
  return gt4Loader;
}

const GeetestCaptcha: React.FC<GeetestCaptchaProps> = ({ captchaId, onSuccess, onClose }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const instanceRef = useRef<GeetestInstance | null>(null);
  // 用 ref 持有回调：避免它进入 useEffect 依赖导致验证实例被反复重建
  const onSuccessRef = useRef(onSuccess);
  onSuccessRef.current = onSuccess;

  const [ready, setReady] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [passed, setPassed] = useState(false);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let disposed = false;
    setReady(false);
    setError('');

    loadGt4()
      .then(() => {
        if (disposed || !window.initGeetest4 || !containerRef.current) return;
        window.initGeetest4(
          { captchaId, product: 'popup', language: 'zho' },
          (captcha) => {
            if (disposed) return;
            instanceRef.current = captcha;

            captcha
              .onReady(() => {
                if (!disposed) setReady(true);
              })
              .onSuccess(async () => {
                const validate = captcha.getValidate();
                // eslint-disable-next-line no-console
                console.log('[Geetest] onSuccess validate=', validate);
                if (!validate) {
                  setError('验证结果获取失败，请点右上角刷新后重试');
                  return;
                }
                setVerifying(true);
                try {
                  const res = await api.auth.captchaGeetestVerify(validate);
                  // eslint-disable-next-line no-console
                  console.log('[Geetest] verify response=', res);
                  if (res.code === 0 && res.data?.ticket) {
                    setPassed(true);
                    // 短暂展示"验证成功"，再通知父组件继续发送验证码
                    setTimeout(() => onSuccessRef.current(res.data.ticket), 400);
                  } else {
                    setError(res.message || '服务端校验未通过，请点右上角刷新后重试');
                  }
                } catch (err) {
                  // eslint-disable-next-line no-console
                  console.error('[Geetest] verify error=', err);
                  const detail = err instanceof Error ? err.message : '未知错误';
                  setError(`校验请求失败：${detail}，请点右上角刷新后重试`);
                } finally {
                  setVerifying(false);
                }
              })
              .onError(() => {
                setError('验证加载失败，请检查网络后重试');
              });

            captcha.appendTo(containerRef.current);
          },
        );
      })
      .catch(() => {
        if (!disposed) setError('无法加载极验组件，请检查网络后重试');
      });

    return () => {
      disposed = true;
      try {
        instanceRef.current?.destroy();
      } catch {
        // 实例尚未完全初始化时 destroy 会抛错，忽略即可
      }
      instanceRef.current = null;
    };
  }, [captchaId, reloadKey]);

  const handleReload = useCallback(() => {
    setPassed(false);
    setError('');
    setReloadKey((k) => k + 1);
  }, []);

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
            <button type="button" onClick={handleReload} title="刷新验证" className="p-1">
              <RefreshCw className="h-4 w-4 text-slate-400 hover:text-indigo-600" />
            </button>
            <button type="button" onClick={onClose} title="关闭" className="p-1">
              <X className="h-4 w-4 text-slate-400 hover:text-slate-700" />
            </button>
          </div>
        </div>

        {/* 极验组件挂载点 */}
        <div className="flex min-h-[160px] items-center justify-center rounded-xl bg-slate-50 py-6">
          <div ref={containerRef} />
          {!ready && !error && (
            <span className="text-xs text-slate-400">加载中…</span>
          )}
        </div>

        {verifying && (
          <p className="text-center text-xs text-indigo-600">正在校验验证结果…</p>
        )}
        {passed && (
          <p className="text-center text-xs text-emerald-600">验证成功，正在发送验证码…</p>
        )}
        {error && <p className="text-xs text-rose-600">{error}</p>}

        <p className="text-[11px] leading-relaxed text-slate-400">
          完成验证后才会发送验证码，可有效防止恶意刷取。
        </p>
      </div>
    </div>
  );
};

export default GeetestCaptcha;
