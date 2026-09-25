import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Compass, ChevronLeft } from 'lucide-react';

/**
 * 404 页面：航站屏风格的"登机口未找到"提示。
 * 替换原先的静默重定向首页，让用户明确知道路径不存在并给出返回出口。
 */
export const NotFound: React.FC = () => {
  const { pathname } = useLocation();
  return (
    <div className="min-h-[60vh] flex items-center justify-center">
      <div className="bg-surface border border-hairline rounded-lg p-8 md:p-12 max-w-md w-full text-center shadow-surface space-y-5">
        <div className="p-4 bg-panel rounded-md inline-flex">
          <Compass className="w-10 h-10 text-steel" strokeWidth={1.5} />
        </div>
        <div className="space-y-1">
          <div className="mono-label text-steel tracking-mono">404 · GATE NOT FOUND</div>
          <h1 className="text-heading-1 text-ink">登机口未找到</h1>
          <p className="text-body-2 text-steel break-all">
            路径 <span className="font-mono text-slate">/{pathname}</span> 不存在或已变更。
          </p>
        </div>
        <Link
          to="/"
          className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-ink hover:bg-slate text-surface rounded-md mono-label uppercase tracking-mono transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          返回信息板首页
        </Link>
      </div>
    </div>
  );
};
