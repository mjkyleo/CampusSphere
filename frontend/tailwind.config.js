/** @type {import('tailwindcss').Config} */
// Material Design 设计令牌：纸张墨水隐喻 / 海拔阴影 / 8dp 网格 / 大胆紫色。
// 保留全部语义 token 名（ink/slate/.../zone.*），只改取值，使 900+ 处 className 自动换肤。
export default {
  content: [
    './index.html',
    './*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './context/**/*.{ts,tsx}',
    './hooks/**/*.{ts,tsx}',
    './pages/**/*.{ts,tsx}',
    './services/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Material 中性色阶（黑/白透明度层级，用实色近似）
        ink: '#212121',        // 主文字（87% black）
        slate: '#616161',      // 次级文字（54% black）
        steel: '#9e9e9e',      // 辅助文字 / 图标
        panel: '#f5f5f5',      // 浅灰面板
        surface: '#ffffff',    // 纸张表面
        ground: '#fafafa',     // 应用背景
        hairline: '#e0e0e0',   // 分隔线
        alert: '#ffb300',
        success: '#00c853',
        error: '#b00020',      // Material error
        // Material 主色 / 强调色
        primary: {
          DEFAULT: '#6200ee',
          dark: '#3700b3',      // 主色变体
          light: '#bb86fc',
          soft: '#f3e5ff',
          hover: '#7c3aed',
        },
        accent: {
          DEFAULT: '#03dac6',
          dark: '#018786',
          soft: '#e0fbf8',
        },
        // 模块区域身份色（Material 调色板）
        zone: {
          home: '#6200ee',
          market: '#c12700',
          course: '#3700b3',
          canteen: '#e65100',
          teammate: '#00897b',
          share: '#7c3aed',
          job: '#558b2f',
          message: '#546e7a',
        },
        'brand-wechat': '#07c160',
        'brand-qq': '#12b7f5',
      },
      fontFamily: {
        ui: ['Roboto', 'Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        display: ['Roboto', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-stat': ['2.75rem', { lineHeight: '1.1', fontWeight: '500' }],
        'heading-1': ['1.75rem', { lineHeight: '1.25', fontWeight: '500' }],
        'heading-2': ['1.25rem', { lineHeight: '1.35', fontWeight: '500' }],
        'heading-3': ['1rem', { lineHeight: '1.45', fontWeight: '500' }],
        'body-1': ['0.9375rem', { lineHeight: '1.6' }],
        'body-2': ['0.8125rem', { lineHeight: '1.55' }],
        caption: ['0.75rem', { lineHeight: '1.5' }],
        'mono-label': ['0.6875rem', { lineHeight: '1.35' }],
        'mono-data': ['0.8125rem', { lineHeight: '1.45' }],
      },
      letterSpacing: { mono: '0.08em' },
      borderRadius: {
        // Material 标准：卡片 rounded-xl（12px），按钮 4-8px
        sm: '0.25rem',
        md: '0.5rem',
        lg: '0.75rem',
        xl: '0.75rem',
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      boxShadow: {
        // Material elevation（1/2/4/8/16dp），硬朗深色阴影
        surface: '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
        elevate: '0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22)',
        'md-2': '0 3px 6px rgba(0,0,0,0.16), 0 3px 6px rgba(0,0,0,0.23)',
        'md-4': '0 6px 10px rgba(0,0,0,0.17), 0 3px 10px rgba(0,0,0,0.15)',
        'md-8': '0 14px 28px rgba(0,0,0,0.25), 0 10px 10px rgba(0,0,0,0.22)',
        'md-16': '0 19px 38px rgba(0,0,0,0.30), 0 15px 12px rgba(0,0,0,0.22)',
        soft: '0 3px 10px rgba(98,0,238,0.24)',
        'soft-lg': '0 8px 20px rgba(98,0,238,0.32)',
        slate: '0 2px 6px rgba(0,0,0,0.16)',
        'slate-lg': '0 6px 14px rgba(0,0,0,0.22)',
        inset: 'inset 0 2px 6px rgba(55,0,179,0.35)',
      },
      transitionTimingFunction: {
        // Material 标准减速曲线
        impeccable: 'cubic-bezier(0.4, 0, 0.2, 1)',
      },
      transitionDuration: {
        feedback: '250ms',
        rerank: '300ms',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
