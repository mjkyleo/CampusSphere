# 组件规范：shadcn/ui 风格适配说明

> 更新：2026-11-28
> 参考：`https://github.com/shadcn-ui/ui.git`
> 目标：借鉴 shadcn 的**组件 API 形态与无障碍规范**，保留项目现有 Material 主题，不引入 Radix（避免 React 19 兼容风险）。

## 1. 基础设施

| 项 | 状态 | 位置 |
|---|---|---|
| `cn()` className 合并 | 新增 | `frontend/lib/utils.ts`（`clsx` + `tailwind-merge`） |
| `class-variance-authority` | 已安装（备用） | `frontend/package.json` |
| `tailwindcss-animate` | 已安装并启用 | `tailwind.config.js` 的 `plugins` |
| 统一组件源文件 | 新增 | `frontend/components/ui/primitives.tsx` |
| barrel 导出 | 更新 | `frontend/components/ui/index.ts` |

## 2. 已实现的组件（对应 shadcn 清单）

| shadcn 组件 | 项目实现 | 说明 |
|---|---|---|
| **Button** | `primitives.tsx` | 6+2 种 variant、4 种 size、`loading`/`asChild` 兼容旧 API；`Button.tsx` 已 re-export，**向后兼容** |
| **Badge** | `primitives.tsx` | 6 种 variant、`dot` 圆点 |
| **Input / Textarea / Label / Field** | `primitives.tsx` | Material 下划线输入框、Field 统一 label/错误/描述 |
| **Card** | `primitives.tsx` | `Card/Header/Title/Content/Footer` 五件套 |
| **Separator** | `primitives.tsx` | 横/竖分隔线，带 `role="separator"` |
| **Skeleton** | `primitives.tsx` | 骨架屏 |
| **Spinner** | `primitives.tsx` | 3 种尺寸，`role="status"` + sr-only 标签 |
| **Alert** | `primitives.tsx` | 4 种 variant，`role="alert"` |
| **Empty** | `primitives.tsx` | 图标+标题+描述+操作区 |
| **Switch** | `primitives.tsx` | `role="switch"` + `aria-checked` |
| **ToggleGroup** | `primitives.tsx` | `role="group"` + `aria-pressed` |
| **Tabs** | `primitives.tsx` | `role="tablist/tab"` + 键盘左右切换 + `aria-selected` |
| **Dialog** | `primitives.tsx` | Esc 关闭、遮罩关闭、焦点恢复、`aria-modal` |
| **Table** | `primitives.tsx` | `Table/Header/Row/Cell` 四件套 |
| **Avatar** | `primitives.tsx` + `ImagePlaceholder` | 图片加载失败自动回退首字母/图标 |
| **Progress** | `primitives.tsx` | `role="progressbar"` |
| **Toast** | `context/ToastContext.tsx` | 改进：a11y、去重、最多 5 条、定时器清理 |

> 未实现 shadcn 清单里的：Accordion / AlertDialog / AspectRatio / Calendar / Carousel / Chart 包装 / Checkbox / Collapsible / Combobox / Command / ContextMenu / Data Table / Date Picker / Drawer / DropdownMenu / HoverCard / InputGroup / InputOTP / Item / Kbd / Menubar / NativeSelect / NavigationMenu / Pagination / Popover / RadioGroup / Resizable / ScrollArea / Select / Sheet / Sidebar / Slider / Sonner / Typography。
>
> 原因：项目当前没有这些模式的真实使用需求。按你的要求「有就优化」，不为凑齐清单引入无用组件。

## 3. 已回填的组件使用点

| 位置 | 改动 |
|---|---|
| `components/ProtectedRoute.tsx`、`AdminRoute.tsx`、`PublicOnlyRoute.tsx` | 内联 spinner → `<Spinner size="lg" />` |
| `context/ToastContext.tsx` | 用 `cn()`，加 `role="status"`/`aria-live`、去重、上限 5 条、unmount 清理定时器 |
| `components/ReportModal.tsx` | 手写遮罩 → `<Dialog>`；textarea → `<Textarea maxLength=500>`；警告 → `<Alert>`；按钮 → 新 `Button variant="destructive" loading` |
| `components/ErrorBoundary.tsx` | 硬编码卡片 → `<Card/Alert/Button>`；增加错误详情展示 |
| `components/ui/ImagePlaceholder.tsx` | 支持 `src`/`name`，Avatar 语义 + 图片失败回退 |

## 4. 验证

- `npm run build`：通过
- `npx tsc --noEmit`：通过
- `e2e/playwright.dev.config.ts` 全功能 E2E：**9/9 通过**（34.3s）

## 5. 后续建议（未做，避免过度改造）

1. **Button 回填**：页面里仍有 100+ 处内联 `<button>`，可逐步替换为统一 `Button`（已在 `primitives.tsx` 备好 `variant/size/loading`）。
2. **Input/Field 回填**：各页面重复的 `inputCls` 可替换为 `Input`/`Field`。
3. **Tabs/Table 回填**：`AdminDashboard` 的内联 tabs 与 3 张原生 table 可替换为对应组件。
4. **Shadcn CLI**：如果后续要完整引入 shadcn（含 Radix 无障碍 primitive），建议先确认 React 19 兼容性，再 `npx shadcn@latest init` 按官方方式生成到 `components/ui/`。
