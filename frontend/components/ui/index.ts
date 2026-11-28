export { Button } from './Button';
export { Board, BoardColumns, BoardRow, DataCell, TextCell, ActionCell } from './Board';
export type { BoardCols } from './Board';
export { PassCard } from './PassCard';
export type { PassSegment } from './PassCard';
export { ImagePlaceholder } from './ImagePlaceholder';

// shadcn/ui 风格基础组件（Material 主题）
export {
  Button as ShadcnButton, Badge, Input, Textarea, Label, Field,
  Card, CardHeader, CardTitle, CardContent, CardFooter,
  Separator, Skeleton, Spinner, Alert, Empty, Switch, ToggleGroup, Tabs,
  Dialog, Table, TableHeader, TableRow, TableCell, Avatar, Progress,
} from './primitives';
export type { ButtonProps } from './primitives';
