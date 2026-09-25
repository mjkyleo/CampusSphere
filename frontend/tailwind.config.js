/** @type {import('tailwindcss').Config} */
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
        ink: '#0B0D10',
        slate: '#1C2127',
        steel: '#6B7178',
        panel: '#E6E8EB',
        surface: '#FFFFFF',
        ground: '#F2F3F5',
        hairline: '#D8DADD',
        alert: '#FFD400',
        success: '#1B6E3C',
        error: '#B3261E',
        // 模块区域身份色（Zone Accent，方案1 已确认）——仅身份位使用，alert 仍唯一管变更
        zone: {
          home: '#0B0D10',
          market: '#B45309',
          course: '#1E4FA0',
          canteen: '#C2410C',
          teammate: '#0F766E',
          share: '#6D28D9',
          job: '#4D7C0F',
          message: '#475569',
        },
      },
      fontFamily: {
        ui: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
        display: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        'display-gate': ['2.75rem', { lineHeight: '1.05', fontWeight: '700' }],
        'heading-1': ['1.75rem', { lineHeight: '1.2', fontWeight: '600' }],
        'heading-2': ['1.25rem', { lineHeight: '1.3', fontWeight: '600' }],
        'heading-3': ['1rem', { lineHeight: '1.4', fontWeight: '600' }],
        'body-1': ['0.9375rem', { lineHeight: '1.5' }],
        'body-2': ['0.8125rem', { lineHeight: '1.45' }],
        caption: ['0.75rem', { lineHeight: '1.4' }],
        'mono-label': ['0.6875rem', { lineHeight: '1.3' }],
        'mono-data': ['0.8125rem', { lineHeight: '1.4' }],
      },
      letterSpacing: {
        mono: '0.08em',
      },
      borderRadius: {
        sm: '0.25rem',
        md: '0.5rem',
        lg: '0.75rem',
      },
      boxShadow: {
        surface: '0 1px 2px rgba(11,13,16,0.06)',
        elevate: '0 6px 20px rgba(11,13,16,0.12)',
      },
      transitionTimingFunction: {
        impeccable: 'cubic-bezier(0.2,0,0.3,1)',
      },
      transitionDuration: {
        feedback: '150ms',
        rerank: '280ms',
      },
    },
  },
  plugins: [],
};
