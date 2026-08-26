
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// 关键：dev 模式下 Vite 对 .css 返回 Content-Type: text/javascript（用 JS 注入样式）。
// 必须用 <script type="module" src="/index.css"> 加载，或在入口 import 才能让样式生效；
// 否则写 <link rel="stylesheet" href="/index.css"> 浏览器拿到的是 JS、当 CSS 解析失败，
// 表现为「页面纯文本流式布局、所有 Tailwind 类失效」（典型的 SPA + importmap 错配）。

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error("Could not find root element to mount to");
}

const root = ReactDOM.createRoot(rootElement);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
