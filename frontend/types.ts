// API Enums matching Backend Specification

export enum UserStatus {
  Normal = 0, // 正常
  Banned = 1, // 封禁
  Pending = 2 // 待审核
}

export enum ItemStatus {
  OnSale = 0, // 上架中
  OffSale = 1, // 已下架
  Sold = 2, // 已售出
  Reserved = 3, // 已保留
  Pending = 4 // 待审核（后台开启发布审核开关后进入该状态）
}

export enum TradeStatus {
  Pending = 0, // 待处理
  InProgress = 1, // 进行中
  Completed = 2, // 已完成
  Cancelled = 3 // 已取消
}

export enum MessageType {
  Text = 0, // 文本
  Image = 1, // 图片
  File = 2 // 文件
}

export enum JobStatus {
  Hiring = 0, // 招聘中
  Closed = 1 // 已关闭
}

export enum SalaryType {
  Hourly = 0,
  Daily = 1,
  Monthly = 2,
  OneTime = 3
}

export enum ApplicationStatus {
  Pending = 0, // 待处理
  Accepted = 1, // 已录用
  Rejected = 2 // 已拒绝
}

export enum TeamStatus {
  Open = 0,
  Recruiting = 0, // 招募中
  Full = 1, // 已满员
  Disbanded = 2, // 已解散
  Closed = 3
}

export enum MemberStatus {
  Pending = 0, // 待确认
  Joined = 1, // 已加入
  Quit = 2 // 已退出
}

export enum ReportStatus {
  Pending = 0, // 待处理
  Processing = 1, // 处理中
  Resolved = 2, // 已解决
  Rejected = 3 // 已驳回
}

export enum ReportAction {
  None = 'none',
  Warning = 'warning',
  ItemOffSale = 'item_offsale',
  UserBan = 'user_ban',
  CommentDelete = 'comment_delete'
}

export type ReportTargetType = 'user' | 'item' | 'message' | 'comment' | 'share' | 'course' | 'stall';
export type ConversationType = 'direct' | 'trade' | 'group';

// API Response Models
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in: number;
}

export interface SendCodeOut {
  debug_code?: string | null;
  expires_in?: number;
}

// 滑块验证（发送验证码前的人机校验）
export interface SliderCaptcha {
  token: string;
  background: string; // 带缺口的背景图（data URI）
  slider: string; // 拼图块（data URI）
  width: number; // 画布宽度（px）
  height: number; // 画布高度（px）
  slider_size: number; // 滑块边长（px）
  y: number; // 缺口纵坐标，滑块需保持同一水平线
  expires_in: number;
}

export interface SliderVerifyResult {
  ticket: string; // 一次性票据，发送验证码时回传
  expires_in: number;
}

export interface CaptchaConfig {
  enabled: boolean;
  /** 当前生效的验证提供方：geetest=极验行为验证；builtin=服务端拼图滑块 */
  provider?: 'geetest' | 'builtin';
  /** provider=geetest 时下发，供前端 initGeetest4 初始化 */
  geetest_id?: string;
}

/** 极验前端验证通过后 getValidate() 的原始结果 */
export interface GeetestValidate {
  lot_number: string;
  captcha_output: string;
  pass_token: string;
  gen_time: string;
}

export interface UserOut {
  id: string;
  username: string;
  email?: string | null;
  phone?: string | null;
  nickname: string;
  avatar?: string | null;
  status: UserStatus;
  role?: string;
  campus?: string;
  major?: string;
  grade?: string;
  bio?: string;
  contact_wx?: string;
  created_at: string;
}

export interface UserProfileOut {
  id: string;
  user_id?: string;
  username?: string;
  nickname: string;
  avatar?: string | null;
  bio?: string;
  campus?: string;
  major?: string;
  school_major?: string;
  grade?: any;
  verified?: boolean;
  role?: string;
  email?: string | null;
  phone?: string | null;
  contact_wx?: string;
  contact_qq?: string;
}

export interface BindingsOut {
  username?: string;
  email?: string | null;
  phone?: string | null;
  wechat_bound?: boolean;
  qq_bound?: boolean;
  oauth?: string[]; // e.g. ['wechat', 'qq']
}

export interface ItemImageIn {
  object_key: string;
  sort_order?: number;
}

export interface ItemImageOut {
  id: string;
  object_key: string;
  sort_order: number;
}

export interface ItemOut {
  id: string;
  owner_id: string;
  owner_nickname?: string;
  owner_avatar?: string;
  title: string;
  description: string;
  price: number; // 单位：分 (cents)
  category: string;
  status: ItemStatus;
  images: ItemImageOut[];
  campus?: string;
  location?: string;
  created_at?: string | null;
  views?: number;
  likes?: number;
  favorites_count?: number;
}

export interface ItemCreate {
  title: string;
  description?: string;
  price: number; // 单位：分
  category?: string;
  campus?: string;
  location?: string;
  images?: ItemImageIn[];
}

export interface ItemUpdate {
  title?: string | null;
  description?: string | null;
  price?: number | null;
  category?: string | null;
  status?: ItemStatus | null;
}

export interface TradeSessionOut {
  id: string;
  item_id: string;
  buyer_id: string;
  seller_id: string;
  status: TradeStatus;
  conversation_id?: string | null;
  item?: ItemOut;
  created_at?: string;
}

export interface MessageOut {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_nickname?: string;
  sender_avatar?: string;
  type: MessageType;
  content: string;
  is_read: boolean;
  created_at: string;
}

export interface ConversationOut {
  id: string;
  conv_type: ConversationType;
  related_id?: string | null;
  related_item?: any;
  target_user?: {
    id: string;
    nickname: string;
    avatar?: string;
  };
  last_message?: any;
  last_message_at?: string;
  updated_at?: string;
  unread_count?: number;
}

export interface CourseOut {
  id: string;
  code: string;
  name: string;
  teacher: string;
  instructor?: string;
  department: string;
  credits: number;
  semester?: string;
  rating?: number;
  reviews_count?: number;
  difficulty?: number;
  workload?: number | string;
  scoring?: number;
  description?: string;
  tags?: string[];
}

export interface CourseCreate {
  code: string;
  name: string;
  teacher?: string;
  credits?: number;
  department?: string;
  semester?: string;
}

export interface CourseReviewOut {
  id: string;
  course_id: string;
  user_id: string;
  user_nickname?: string;
  user_avatar?: string;
  rating: number; // 1-5
  content: string;
  teacher_rating?: number;
  difficulty?: number;
  workload?: any;
  grading_policy?: string;
  scoring?: number;
  created_at?: string;
  likes?: number;
  helpful_count?: number;
  is_anonymous?: boolean;
}

export interface DishOut {
  id: string;
  stall_id: string;
  name: string;
  price: number; // 单位：分
  rating?: number;
  image?: string;
  reviews_count?: number;
  tags?: string[];
}

export interface StallOut {
  id: string;
  canteen_id: string;
  canteen_name?: string;
  name: string;
  cuisine_type?: string;
  description?: string;
  popular_dish?: string;
  rating?: number;
  image?: string;
  dishes?: any[];
}

export type CanteenStallOut = StallOut;

export interface CanteenOut {
  id: string;
  name: string;
  location: string;
  opening_hours?: string;
  description?: string;
  rating?: number;
  image?: string;
  status?: string;
  stalls?: StallOut[];
}

export interface CanteenReviewOut {
  id: string;
  canteen_id?: string;
  stall_id?: string;
  dish_name?: string;
  dish_id?: string;
  user_id: string;
  user_nickname?: string;
  rating: number;
  content: string;
  price_cents?: number;
  created_at?: string;
}

export interface JobOut {
  id: string;
  poster_id?: string;
  poster_name?: string;
  title: string;
  description: string;
  company: string;
  salary_cents: number; // 单位：分
  salary?: number; // 单位：分
  salary_type: SalaryType | string;
  category?: string;
  status?: JobStatus;
  location: string;
  contact: string;
  requirements?: string;
  time_requirement?: string;
  verified?: boolean;
  created_at?: string;
}

export interface JobCreate {
  title: string;
  company: string;
  salary_cents: number;
  salary_type: SalaryType;
  location: string;
  contact: string;
  description: string;
  requirements?: string;
  category?: string;
}

export interface JobApplicationOut {
  id: string;
  job_id: string;
  job_title?: string;
  applicant_id: string;
  applicant_name?: string;
  status: ApplicationStatus;
  note: string;
  created_at?: string;
}

export interface ShareCommentOut {
  id: string;
  share_id: string;
  user_id: string;
  user_nickname?: string;
  content: string;
  created_at: string;
}

export interface ShareOut {
  id: string;
  owner_id?: string;
  owner_nickname?: string;
  title: string;
  description: string;
  file_key?: string;
  file_url?: string;
  category: string;
  downloads: number;
  download_url?: string | null;
  file_size?: string;
  tags?: string[];
  created_at?: string;
  likes?: number;
  comments_count?: number;
}

export interface ShareCreate {
  title: string;
  description: string;
  category: string;
  file_url: string;
  file_size?: string;
  tags?: string[];
}

export interface TeamMemberOut {
  id: string;
  team_id: string;
  user_id: string;
  user_nickname?: string;
  role: string;
  status: MemberStatus;
  joined_at?: string;
}

export interface TeamOut {
  id: string;
  creator_id: string;
  creator_nickname?: string;
  creator_name?: string;
  title: string;
  description: string;
  required_roles: string;
  status?: TeamStatus;
  category?: string;
  member_count?: number;
  current_members?: number;
  target_count?: number;
  max_members?: number;
  time?: string;
  location?: string;
  contact_info?: string;
  created_at?: string;
  members?: TeamMemberOut[];
}

export interface TeamCreate {
  title: string;
  category: string;
  description: string;
  required_roles: string;
  contact_info?: string;
  max_members: number;
}

export interface ReportLogOut {
  id: string;
  operator_id: string;
  action: string;
  note: string;
  created_at?: string;
}

export interface ReportOut {
  id: string;
  reporter_id: string;
  reporter_nickname?: string;
  target_type: ReportTargetType;
  target_id: string;
  target_title?: string;
  reason: string;
  status: ReportStatus;
  handled_by?: string | null;
  logs?: ReportLogOut[];
  created_at?: string;
}

export interface AdminReportOut {
  id: string;
  reporter_id: string;
  target_type: ReportTargetType;
  target_id: string;
  reason: string;
  status: ReportStatus;
  action?: ReportAction;
  feedback?: string;
  created_at: string;
}

export interface AdminOverviewOut {
  dau: number;
  mau: number;
  total_users: number;
  total_items: number;
  total_trades: number;
  pending_reports: number;
}

export interface AuditLogOut {
  id: string;
  admin_username: string;
  action: string;
  target_type: string;
  target_id: string;
  details: string;
  created_at: string;
}

export interface EmailRegisterConfig {
  enabled?: boolean;
  domains?: string[];
  pattern?: string;
}

export interface ItemReviewConfig {
  enabled: boolean;
}

export interface AiFeatureConfig {
  enabled: boolean;
  model: string;
}

export interface AiStatusOut {
  enabled: boolean;
  available: boolean;
  message: string;
}

/** 管理端获取 AI 配置：配置项 + 实时运行状态（/api/admin/ai/config GET） */
export interface AiConfig {
  enabled: boolean;
  model: string;
  status: AiStatusOut;
}

/** 更新 AI 配置的请求体（/api/admin/ai/config PUT） */
export type AiConfigUpdate = Pick<AiFeatureConfig, 'enabled' | 'model'>;

export interface AdminOut {
  id: string;
  username: string;
  role_id?: string | null;
  disabled?: boolean;
  permissions?: string[];
}
