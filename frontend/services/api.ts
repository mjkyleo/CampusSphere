import {
  ApiResponse, TokenResponse, UserOut, UserProfileOut, BindingsOut,
  ItemOut, ItemCreate, ItemUpdate, ItemStatus,
  TradeSessionOut, TradeStatus,
  ConversationOut, MessageOut, MessageType,
  CourseOut, CourseCreate, CourseReviewOut,
  CanteenOut, StallOut, DishOut, CanteenReviewOut, CanteenConfig,
  JobOut, JobCreate, JobApplicationOut, ApplicationStatus, JobStatus,
  ShareOut, ShareCreate, ShareCommentOut,
  TeamOut, TeamCreate, TeamMemberOut, TeamStatus, MemberStatus,
  ReportOut, ReportTargetType, ReportStatus,
  EmailRegisterConfig, ItemReviewConfig, AdminOut,
  AiFeatureConfig, AiStatusOut, AiConfig, AiConfigUpdate,
  SendCodeOut, SliderCaptcha, SliderVerifyResult, CaptchaConfig, GeetestValidate
} from '../types.ts';

// Storage keys
const ACCESS_TOKEN_KEY = 'cs_access_token';
const REFRESH_TOKEN_KEY = 'cs_refresh_token';
const ADMIN_ACCESS_TOKEN_KEY = 'cs_admin_access_token';
const ADMIN_REFRESH_TOKEN_KEY = 'cs_admin_refresh_token';
const ADMIN_GATEWAY_TOKEN_KEY = 'cs_admin_gateway_token';
const USER_PROFILE_KEY = 'cs_user_profile';
const ADMIN_PROFILE_KEY = 'cs_admin_profile';
const MOCK_STORAGE_KEY = 'cs_mock_db_v3';

export const getStoredAccessToken = (): string | null => localStorage.getItem(ACCESS_TOKEN_KEY);
export const getStoredRefreshToken = (): string | null => localStorage.getItem(REFRESH_TOKEN_KEY);
export const getStoredAdminAccessToken = (): string | null => localStorage.getItem(ADMIN_ACCESS_TOKEN_KEY);
export const getStoredAdminRefreshToken = (): string | null => localStorage.getItem(ADMIN_REFRESH_TOKEN_KEY);
export const getStoredAdminGatewayToken = (): string | null => localStorage.getItem(ADMIN_GATEWAY_TOKEN_KEY);
export const setAdminGatewayToken = (token: string) => localStorage.setItem(ADMIN_GATEWAY_TOKEN_KEY, token);
export const clearAdminGatewayToken = () => localStorage.removeItem(ADMIN_GATEWAY_TOKEN_KEY);

export const setAuthTokens = (tokens: TokenResponse) => {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
};

export const setAdminAuthTokens = (tokens: TokenResponse) => {
  localStorage.setItem(ADMIN_ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(ADMIN_REFRESH_TOKEN_KEY, tokens.refresh_token);
};

export const clearAuthTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_PROFILE_KEY);
};

export const clearAdminAuthTokens = () => {
  localStorage.removeItem(ADMIN_ACCESS_TOKEN_KEY);
  localStorage.removeItem(ADMIN_REFRESH_TOKEN_KEY);
  localStorage.removeItem(ADMIN_PROFILE_KEY);
  localStorage.removeItem(ADMIN_GATEWAY_TOKEN_KEY);
};

// Helper: Format price from cents (分) to Yuan string
export const formatPrice = (cents: number | undefined | null): string => {
  if (cents === undefined || cents === null || isNaN(cents)) return '0.00';
  return (cents / 100).toFixed(2);
};

// Helper: Convert Yuan input to cents (分)
export const toCents = (yuan: number | string): number => {
  const num = typeof yuan === 'string' ? parseFloat(yuan) : yuan;
  if (isNaN(num)) return 0;
  return Math.round(num * 100);
};

// Initial Seed Data for fallback local state
const INITIAL_MOCK_DATA = {
  currentUser: {
    id: 'usr-001',
    user_id: 'usr-001',
    username: 'campus_student',
    nickname: '阿强同学',
    avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
    bio: '计算机科学与技术大三学生，热爱摄影与羽毛球。',
    school_major: '信息与计算机科学学院 / 软件工程',
    campus: '主校区',
    major: '计算机科学与技术',
    grade: '2023级',
    verified: true,
    email: 'qiang@example.edu.cn',
    phone: '13800138000',
    contact_wx: 'qiang_campus_dev'
  } as UserProfileOut,

  bindings: {
    username: 'campus_student',
    email: 'qiang@example.edu.cn',
    phone: '13800138000',
    oauth: ['wechat']
  } as BindingsOut,

  emailConfig: {
    enabled: true,
    domains: ['example.edu.cn', 'campus.edu', 'university.edu.cn'],
    pattern: '.*@.*\\.edu(\\.cn)?'
  } as EmailRegisterConfig,

  items: [
    {
      id: 'itm-1',
      owner_id: 'usr-002',
      owner_nickname: '学长在线卖货',
      owner_avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80',
      title: 'iPad Pro 11寸 256G (M2芯片 极新)',
      description: '基本没怎么用过，一直带套贴膜。电池健康98%。配件齐全，附赠原装充电器和磁吸保护壳。因为换了MacBook所以这个闲置了，可面交验机。',
      price: 350000, // 3500.00 元 (分)
      category: '电子产品',
      status: ItemStatus.OnSale,
      images: [
        { id: 'img-1-1', object_key: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=800&auto=format&fit=crop&q=80', sort_order: 0 },
        { id: 'img-1-2', object_key: 'https://images.unsplash.com/photo-1561154464-82e9adf32764?w=800&auto=format&fit=crop&q=80', sort_order: 1 }
      ],
      campus: '主校区',
      location: '主图书馆门前 / 12号宿舍楼下',
      created_at: new Date(Date.now() - 3600000 * 5).toISOString(),
      views: 186,
      likes: 24,
      favorites_count: 12
    },
    {
      id: 'itm-2',
      owner_id: 'usr-001',
      owner_nickname: '阿强同学',
      owner_avatar: 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80',
      title: '99新 捷安特山地公路车 (带密码锁+前车灯)',
      description: '大一入学购入，平时主要用于校内往返教学区。换了电动滑板车现出给有缘学弟学妹，刹车变速极为灵敏，已保养上油。',
      price: 45000, // 450.00 元
      category: '交通代步',
      status: ItemStatus.OnSale,
      images: [
        { id: 'img-2-1', object_key: 'https://images.unsplash.com/photo-1485965120184-e220f721d03e?w=800&auto=format&fit=crop&q=80', sort_order: 0 }
      ],
      campus: '南校区',
      location: '北门车棚',
      created_at: new Date(Date.now() - 3600000 * 12).toISOString(),
      views: 95,
      likes: 18,
      favorites_count: 7
    },
    {
      id: 'itm-3',
      owner_id: 'usr-003',
      owner_nickname: '文学院小林',
      owner_avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&auto=format&fit=crop&q=80',
      title: '《西方哲学史》+《现代文学经典解析》精装全套',
      description: '考研上岸全套专业参考书，内含高分学姐重点荧光笔标注与思维导图笔记。买书送考研历年真题纸质打印版！',
      price: 6800, // 68.00 元
      category: '图书教材',
      status: ItemStatus.OnSale,
      images: [
        { id: 'img-3-1', object_key: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80', sort_order: 0 }
      ],
      campus: '主校区',
      location: '文科楼中庭',
      created_at: new Date(Date.now() - 3600000 * 24).toISOString(),
      views: 312,
      likes: 45,
      favorites_count: 29
    },
    {
      id: 'itm-4',
      owner_id: 'usr-004',
      owner_nickname: '球鞋研究所',
      owner_avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80',
      title: '索尼 WH-1000XM4 无线降噪头戴式耳机',
      description: '考研自习室神级降噪神器，隔音效果立竿见影。箱说全，耳罩皮革完好无磨损，附赠便携收纳硬包与音频转接线。',
      price: 98000, // 980.00 元
      category: '数码影音',
      status: ItemStatus.OnSale,
      images: [
        { id: 'img-4-1', object_key: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&auto=format&fit=crop&q=80', sort_order: 0 }
      ],
      campus: '主校区',
      location: '第四教学楼一楼大厅',
      created_at: new Date(Date.now() - 3600000 * 30).toISOString(),
      views: 420,
      likes: 67,
      favorites_count: 38
    }
  ] as ItemOut[],

  trades: [] as TradeSessionOut[],

  conversations: [
    {
      id: 'conv-1',
      conv_type: 'direct' as const,
      target_user: {
        id: 'usr-002',
        nickname: '学长在线卖货',
        avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'
      },
      last_message: {
        id: 'msg-1-2',
        conversation_id: 'conv-1',
        sender_id: 'usr-002',
        type: MessageType.Text,
        content: '同学你好，iPad还在的，明天下午可以在图书馆门口当面试机。',
        is_read: false,
        created_at: new Date(Date.now() - 1800000).toISOString()
      },
      unread_count: 1,
      updated_at: new Date(Date.now() - 1800000).toISOString(),
      related_item: {
        id: 'itm-1',
        owner_id: 'usr-002',
        title: 'iPad Pro 11寸 256G (M2芯片 极新)',
        description: '',
        price: 350000,
        category: '电子产品',
        status: ItemStatus.OnSale,
        images: [{ id: 'img-1-1', object_key: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=800&auto=format&fit=crop&q=80', sort_order: 0 }]
      }
    }
  ] as ConversationOut[],

  messages: [
    {
      id: 'msg-1-1',
      conversation_id: 'conv-1',
      sender_id: 'usr-001',
      type: MessageType.Text,
      content: '学长你好！看到你发布的iPad Pro，请问目前电池健康度和配件都还在吗？可以小刀一点吗？',
      is_read: true,
      created_at: new Date(Date.now() - 3600000).toISOString()
    },
    {
      id: 'msg-1-2',
      conversation_id: 'conv-1',
      sender_id: 'usr-002',
      type: MessageType.Text,
      content: '同学你好，iPad还在的，明天下午可以在图书馆门口当面试机。',
      is_read: false,
      created_at: new Date(Date.now() - 1800000).toISOString()
    }
  ] as MessageOut[],

  courses: [
    {
      id: 'crs-1',
      code: 'CS201',
      name: '数据结构与算法',
      teacher: '张伟 教授',
      instructor: '张伟 教授',
      department: '信息与计算机科学学院',
      credits: 4,
      semester: '2024-2025 秋季学期',
      rating: 4.8,
      reviews_count: 158,
      tags: ['专业必修', '硬核干货', '给分厚道', '代码量大'],
      difficulty: 4.2,
      workload: 3.8,
      scoring: 4.6,
      description: '计算机专业核心基础课程，涵盖链表、树、图、高级排序及动态规划算法设计与分析。'
    },
    {
      id: 'crs-2',
      code: 'MATH102',
      name: '高等线性代数',
      teacher: '李娜 副教授',
      instructor: '李娜 副教授',
      department: '数学与统计学院',
      credits: 3,
      semester: '2024-2025 春季学期',
      rating: 3.4,
      reviews_count: 94,
      tags: ['公共基础', '概念抽象', '期末较难', '认真学能过'],
      difficulty: 4.7,
      workload: 4.1,
      scoring: 3.2,
      description: '包括线性空间、特征值分解、Jordan标准型与二次型理论，考查严密数学推导与计算。'
    },
    {
      id: 'crs-3',
      code: 'ART305',
      name: '现代陶艺创作与赏析',
      teacher: '王德才 副教授',
      instructor: '王德才 副教授',
      department: '艺术设计学院',
      credits: 2,
      semester: '2024-2025 全学年',
      rating: 4.9,
      reviews_count: 67,
      tags: ['通识美育', '动手实践', '氛围轻松', '满绩神课'],
      difficulty: 1.5,
      workload: 2.0,
      scoring: 4.9,
      description: '通识美育公选课，在陶艺工作室亲手体验拉胚、修坯与烧窑，结课提交一件原创陶艺作品。'
    },
    {
      id: 'crs-4',
      code: 'AI401',
      name: '深度学习与计算机视觉',
      teacher: '陈俊 教授',
      instructor: '陈俊 教授',
      department: '人工智能学院',
      credits: 3,
      semester: '2024-2025 秋季学期',
      rating: 4.6,
      reviews_count: 82,
      tags: ['前沿科技', '大作业答辩', '支持GPU算力', '竞赛加分'],
      difficulty: 4.0,
      workload: 3.5,
      scoring: 4.5,
      description: '讲授CNN、Transformer、Diffusion与YOLO目标检测前沿网络，提供实验室GPU算力支持完成期末项目。'
    }
  ] as CourseOut[],

  courseReviews: [
    {
      id: 'crev-1-1',
      course_id: 'crs-1',
      user_id: 'usr-005',
      user_nickname: '码农小明',
      rating: 5,
      teacher_rating: 5,
      workload: '适中',
      grading_policy: '给分较好，看重平时',
      difficulty: 4.0,
      scoring: 4.8,
      content: '张老师讲课深入浅出，PPT非常清晰！虽然每周有LeetCode风格的编程作业，但只要按时提交，期末考试绝大部分都是平时讲过的题型变形，给分非常大方！',
      helpful_count: 32,
      likes: 32,
      created_at: '2025-01-15'
    },
    {
      id: 'crev-1-2',
      course_id: 'crs-1',
      user_id: 'usr-006',
      user_nickname: '算法狂魔',
      rating: 5,
      teacher_rating: 5,
      workload: '适中',
      grading_policy: '给分较好，看重平时',
      difficulty: 4.2,
      scoring: 4.5,
      content: '计算机系必选好课！答疑群里老师和助教回复都很迅速，期末还会划重点复习课，推荐大二同学提前选修！',
      helpful_count: 19,
      likes: 19,
      created_at: '2025-01-10'
    }
  ] as CourseReviewOut[],

  canteens: [
    {
      id: 'cant-1',
      name: '第一学生餐厅 (学一食堂)',
      location: '学生生活区北侧 (邻近1-4号宿舍楼)',
      opening_hours: '06:30 - 22:30',
      description: '两层超大就餐区，一楼大众快餐自选与早点面食，二楼特色风味档口。',
      rating: 4.8,
      status: '营业中',
      stalls: [
        {
          id: 'stl-1-1',
          canteen_id: 'cant-1',
          name: '兰州正宗牛肉拉面',
          cuisine_type: '清真面食',
          description: '师傅现拉现煮，大骨高汤熬制，油泼辣子香而不燥。',
          popular_dish: '招牌传统红烧牛肉拉面',
          rating: 4.9,
          dishes: ['招牌牛肉拉面 (细/二细/韭叶)', '干拌臊子面', '葱爆牛肉盖浇饭', '现烤羊肉串']
        },
        {
          id: 'stl-1-2',
          canteen_id: 'cant-1',
          name: '川味老坛酸菜鱼 & 水煮肉片',
          cuisine_type: '川湘风味',
          description: '现称黑鱼无刺鲜嫩，老坛酸菜酸爽开胃，免费加米饭。',
          popular_dish: '金汤酸菜无刺黑鱼饭',
          rating: 4.7,
          dishes: ['金汤酸菜无刺黑鱼饭', '川味麻辣水煮肉片套餐', '番茄浓汤巴沙鱼']
        },
        {
          id: 'stl-1-3',
          canteen_id: 'cant-1',
          name: '岭南广式烧腊档',
          cuisine_type: '粤式烧味',
          description: '正宗明炉烧鸭与蜜汁叉烧，搭配半颗卤蛋与时令蔬菜。',
          popular_dish: '脆皮烧鸭双拼饭',
          rating: 4.8,
          dishes: ['蜜汁叉烧饭', '明炉脆皮烧鸭饭', '豉油鸡腿饭', '原盅老火炖鸡汤']
        }
      ]
    },
    {
      id: 'cant-2',
      name: '清雅清真风味餐厅',
      location: '清真饮食专区 (学生活动中心西侧)',
      opening_hours: '07:00 - 21:00',
      description: '全清真认证餐厅，提供地道新疆大盘鸡、手抓饭与羊肉手揪面。',
      rating: 4.9,
      status: '营业中',
      stalls: [
        {
          id: 'stl-2-1',
          canteen_id: 'cant-2',
          name: '西域风情手抓饭与大盘鸡',
          cuisine_type: '西北风味',
          description: '黄胡萝卜与羊排慢火焖饭，大盘鸡配宽皮带面。',
          popular_dish: '新疆经典羊排手抓饭',
          rating: 4.9,
          dishes: ['新疆羊排手抓饭 (配小菜)', '秘制大盘鸡拌面 (中份/大份)', '自制酸奶']
        }
      ]
    }
  ] as CanteenOut[],

  canteenReviews: [
    {
      id: 'crev-1',
      canteen_id: 'cant-1',
      stall_id: 'stl-1-1',
      dish_name: '招牌传统红烧牛肉拉面',
      user_id: 'usr-001',
      user_nickname: '阿强同学',
      rating: 5,
      price_cents: 1400,
      content: '面条劲道汤头鲜美，辣椒油特别香！师傅拉面动作超利落，每次下课必来一碗！',
      created_at: new Date(Date.now() - 3600000 * 24).toISOString()
    }
  ] as CanteenReviewOut[],

  jobs: [
    {
      id: 'job-1',
      poster_id: 'usr-008',
      poster_name: '阳光辅导中心 (个人招聘)',
      title: '初二数理化周末一对一家教',
      description: '辅导初二男生数学与物理基础，查漏补缺，每周六/周日下午授课2小时。要求耐心细致，理工科大二以上优先。',
      company: '个人招聘 (校友家长)',
      salary_cents: 15000, // 150.00 元/小时
      salary: 15000,
      salary_type: 'hour',
      category: '家教辅导',
      status: JobStatus.Hiring,
      location: '学校东门外阳光丽景小区 (步行10分钟)',
      contact: '微信: ygzx_edu / 手机: 13900001111',
      time_requirement: '每周六 14:00 - 16:00',
      verified: true,
      created_at: '1天前'
    },
    {
      id: 'job-2',
      poster_id: 'usr-009',
      poster_name: '校勤工助学管理中心',
      title: '中心图书馆期刊部学生助理 (勤工助学)',
      description: '负责图书馆期刊图书整理上架、借阅自助机维护与秩序引导。工作环境安静，支持在岗自习。',
      company: '校图书馆期刊部',
      salary_cents: 2500, // 25.00 元/小时
      salary: 2500,
      salary_type: 'hour',
      category: '校内勤工',
      status: JobStatus.Hiring,
      location: '中心图书馆三楼中文期刊阅览室',
      contact: '校内内线: 88201234 / 办公室: 图书馆302',
      time_requirement: '周一至周五 无课时段排班 (每周需满8小时)',
      verified: true,
      created_at: '3天前'
    },
    {
      id: 'job-3',
      poster_id: 'usr-010',
      poster_name: '极客咖啡厅',
      title: '创客空间咖啡吧台见习咖啡师/收银',
      description: '负责咖啡制作、甜点陈列及收银结账。提供专业咖啡拉花培训，工作日提供免费员工餐与咖啡饮品。',
      company: '校园创客空间咖啡部',
      salary_cents: 3000, // 30.00 元/小时
      salary: 3000,
      salary_type: 'hour',
      category: '餐饮零售',
      status: JobStatus.Hiring,
      location: '大学生活动中心一楼',
      contact: '到店面试找店长 / 微信: geek_cafe_hr',
      time_requirement: '周末或晚班 17:00 - 21:30',
      verified: true,
      created_at: '4天前'
    }
  ] as JobOut[],

  jobApplications: [] as JobApplicationOut[],

  shares: [
    {
      id: 'shr-1',
      owner_id: 'usr-001',
      owner_nickname: '阿强同学',
      title: '2024-2025 数据结构期末复习思维导图+高频考点汇总.pdf',
      description: '学长呕心沥血整理的知识点框架！涵盖链表、二叉树、图算法遍历代码模板及常见选择填空易错点。',
      file_key: 'shares/data_structure_cheat_sheet.pdf',
      file_url: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80',
      category: '课程课件',
      downloads: 420,
      file_size: '4.8 MB',
      created_at: '2天前',
      likes: 88,
      comments_count: 24
    },
    {
      id: 'shr-2',
      owner_id: 'usr-003',
      owner_nickname: '小林同学',
      title: '保姆级考研英语一真题长难句拆解与作文模板.zip',
      description: '包含近10年真题经典阅读句型语法分析、小作文信件模板与大作文图表万能金句库，无保留分享。',
      file_key: 'shares/kaoyan_english_pack.zip',
      file_url: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80',
      category: '考研升学',
      downloads: 780,
      file_size: '12.4 MB',
      created_at: '4天前',
      likes: 156,
      comments_count: 51
    },
    {
      id: 'shr-3',
      owner_id: 'usr-007',
      owner_nickname: '羽协队长',
      title: '全校体育馆各时段抢场脚本与空闲场地规律指南.md',
      description: '详细总结了气膜馆、风雨操场羽毛球馆各时段开放规则和成功预订的技巧，建议收藏！',
      file_key: 'shares/badminton_court_tips.md',
      file_url: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80',
      category: '生活经验',
      downloads: 310,
      file_size: '150 KB',
      created_at: '1周前',
      likes: 62,
      comments_count: 18
    }
  ] as ShareOut[],

  shareComments: [
    {
      id: 'shrc-1',
      share_id: 'shr-1',
      user_id: 'usr-003',
      user_nickname: '学弟小张',
      content: '太及时了！图遍历和拓扑排序的图画得非常清晰，救了期末大命！',
      created_at: '昨天 15:30'
    }
  ] as ShareCommentOut[],

  teams: [
    {
      id: 'tm-1',
      creator_id: 'usr-001',
      creator_nickname: '阿强同学',
      creator_name: '阿强同学',
      title: '2025 全国大学生数学建模竞赛 (国赛) 组队 3缺1',
      description: '目前已有计科大三 (负责编程实现与算法优化)、数学院大三 (负责模型推导与公式证明)。现招募一名负责论文排版写作 (熟练掌握LaTeX与论文绘图) 的队友！',
      required_roles: '论文撰写 / LaTeX排版 / 数据可视化',
      status: TeamStatus.Recruiting,
      member_count: 2,
      current_members: 2,
      target_count: 3,
      max_members: 3,
      time: '暑期集训 + 9月国赛开赛',
      location: '图书馆研讨室 / 线上腾讯会议',
      category: '学科竞赛',
      contact_info: '微信: qiang_campus_dev',
      created_at: '1天前',
      members: [
        { id: 'tmm-1', team_id: 'tm-1', user_id: 'usr-001', user_nickname: '阿强同学', role: '算法与编程', status: MemberStatus.Joined },
        { id: 'tmm-2', team_id: 'tm-1', user_id: 'usr-011', user_nickname: '李思思 (数学系)', role: '数学建模', status: MemberStatus.Joined }
      ]
    },
    {
      id: 'tm-2',
      creator_id: 'usr-012',
      creator_nickname: '羽毛球爱好者',
      creator_name: '羽毛球爱好者',
      title: '周五晚上 19:00-21:00 气膜馆羽毛球双打 4缺2',
      description: '已订到2号场地2小时，目前2个男生（中羽3级水平），诚邀2位球友一起拉高远球打双打，AA场地费约15元/人。',
      required_roles: '双打球友 (男女不限，能稳定接发球)',
      status: TeamStatus.Recruiting,
      member_count: 2,
      current_members: 2,
      target_count: 4,
      max_members: 4,
      time: '本周五 19:00 - 21:00',
      location: '东区气膜体育馆2号场',
      category: '运动搭子',
      contact_info: '微信: badminton_lover_99',
      created_at: '2天前',
      members: [
        { id: 'tmm-3', team_id: 'tm-2', user_id: 'usr-012', user_nickname: '羽毛球爱好者', role: '发起人', status: MemberStatus.Joined }
      ]
    }
  ] as TeamOut[],

  reports: [] as ReportOut[],

  adminUsers: [
    { id: 'usr-001', username: 'campus_student', nickname: '阿强同学', email: 'qiang@example.edu.cn', status: 0, created_at: '2024-09-01' },
    { id: 'usr-002', username: 'senior_seller', nickname: '学长在线卖货', email: 'seller@example.edu.cn', status: 0, created_at: '2024-09-05' },
    { id: 'usr-003', username: 'lin_arts', nickname: '文学院小林', email: 'lin@example.edu.cn', status: 0, created_at: '2024-10-12' },
    { id: 'usr-999', username: 'bad_user', nickname: '虚假广告发布者', email: 'spam@bad.com', status: 1, created_at: '2024-12-01' }
  ]
};

// Helper: load/save mock database from localStorage
const getMockDB = () => {
  try {
    const raw = localStorage.getItem(MOCK_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return INITIAL_MOCK_DATA;
};

const saveMockDB = (data: any) => {
  try {
    localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(data));
  } catch {}
};

// ---- Token refresh with concurrency control ----
// Ensures that when multiple concurrent requests receive a 401, only a single
// refresh is performed. All waiting requests share the same refresh Promise.
let isRefreshing = false;
let refreshPromise: Promise<RefreshResult> | null = null;

type RefreshResult =
  | { ok: true; token: string }
  | { ok: false; reason: 'network' | 'rejected' | 'no-token' };

/**
 * Redirect the browser to the login page.
 * Guarded against repeated calls and the login page itself.
 */
function redirectToLogin(admin = false, reason?: string): void {
  // 管理员登录独立地址 /admin/login；已在该页或普通登录页时不重复跳转
  if (
    typeof window !== 'undefined' &&
    window.location.pathname !== '/login' &&
    window.location.pathname !== '/admin/login'
  ) {
    if (admin) {
      window.location.href = '/admin/login';
      return;
    }
    const params: string[] = [];
    if (reason) params.push(`reason=${encodeURIComponent(reason)}`);
    window.location.href = `/login${params.length > 0 ? `?${params.join('&')}` : ''}`;
  }
}

/**
 * Perform a single token refresh request against the backend.
 * Uses a raw fetch (not the request() wrapper) to avoid recursion.
 * Returns the new access_token on success, or the failure reason.
 */
async function doRefreshToken(): Promise<RefreshResult> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return { ok: false, reason: 'no-token' };

  try {
    const res = await fetch('/api/auth/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    let data: any = null;
    try {
      data = await res.json();
    } catch {
      // 响应非 JSON —— 后端不可达或代理错误
      return { ok: false, reason: 'network' };
    }
    // Backend returns { code: 0, data: { access_token, refresh_token, ... } }
    if (res.ok && data.code === 0 && data.data?.access_token) {
      setAuthTokens(data.data);
      return { ok: true, token: data.data.access_token as string };
    }
    // HTTP 401 或业务码非 0 —— refresh token 被后端拒绝（已失效/已吊销/过期）
    return { ok: false, reason: 'rejected' };
  } catch {
    // fetch 抛错 —— 网络层失败
    return { ok: false, reason: 'network' };
  }
}

/**
 * Get a fresh access token, ensuring only one refresh runs at a time.
 * Concurrent callers will await the same in-flight Promise.
 */
async function refreshTokenIfNeeded(): Promise<RefreshResult> {
  // If a refresh is already in progress, wait for the existing promise
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = doRefreshToken();

  try {
    return await refreshPromise;
  } finally {
    isRefreshing = false;
    refreshPromise = null;
  }
}

// Unified request handler
// softAuth: 可选，置为 true 时 401 刷新失败不强制跳转登录页，
// 而是返回 40100 让调用方优雅降级（适用于未读消息等非关键请求）。
export async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  softAuth = false
): Promise<ApiResponse<T>> {
  const isAdminRequest = endpoint.startsWith('/api/admin/');
  const token = isAdminRequest ? getStoredAdminAccessToken() : getStoredAccessToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {})
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // 管理端请求自动附带网关令牌（由 /api/admin/discover 换取并缓存于 sessionStorage），
  // 缺失时后端一律 404，从而"隐藏"管理接口的可达性。
  if (isAdminRequest) {
    const gw = getStoredAdminGatewayToken();
    if (gw) {
      headers['X-Admin-Gateway'] = gw;
    }
  }

  try {
    const res = await fetch(endpoint, {
      ...options,
      headers
    });

    // Parse JSON — may fail for non-JSON responses (e.g., proxy HTML error
    // when the backend is completely unreachable)
    let data: any = null;
    try {
      data = await res.json();
    } catch {
      // Non-JSON response — backend likely unavailable, fall through to Mock
    }

    // Handle 401 unauthorized — the backend returns HTTP 200 with code 40100
    if (data && data.code === 40100) {
      if (isAdminRequest) {
        // 管理员 token 不支持 refresh，直接清除并跳转管理员登录
        clearAdminAuthTokens();
        redirectToLogin(true);
        return data as ApiResponse<T>;
      }
      // Attempt token refresh (concurrent 401s share a single refresh)
      const result = await refreshTokenIfNeeded();
      if (result.ok) {
        // Retry original request with the refreshed access token
        const retryRes = await fetch(endpoint, {
          ...options,
          headers: { ...headers, Authorization: `Bearer ${result.token}` }
        });
        try {
          const retryData = await retryRes.json();
          if (retryData) {
            return retryData as ApiResponse<T>;
          }
        } catch {
          // Retry returned non-JSON — fall through to Mock below
        }
      } else if ('reason' in result) {
        // result 已收窄为失败分支 { ok: false; reason: ... }
        if (result.reason === 'rejected') {
          // 可能是其他标签页已刷新成功导致本地 refresh token 被后端吊销：
          // 重读一次本地 access token，若已有新值则直接用新 token 重试。
          const latest = getStoredAccessToken();
          if (latest && latest !== token) {
            const retryRes = await fetch(endpoint, {
              ...options,
              headers: { ...headers, Authorization: `Bearer ${latest}` }
            });
            try {
              const retryData = await retryRes.json();
              if (retryData) {
                return retryData as ApiResponse<T>;
              }
            } catch {
              // Retry returned non-JSON — fall through to Mock below
            }
          }
        }
        // Refresh 失败说明会话已失效；网络错误时保留登录态（后端不可达）。
        // softAuth 模式不强制踢出，返回 40100 让调用方优雅降级。
        if (!softAuth && result.reason !== 'network') {
          clearAuthTokens();
          redirectToLogin(false, 'session_expired');
        }
      }
      // Return the original 40100 error so callers can handle gracefully
      return data as ApiResponse<T>;
    }

    // 认证成功响应自动保存令牌（login / phone-login / email-register / admin-login）
    if (data && data.code === 0 && data.data && typeof data.data.access_token === 'string') {
      if (isAdminRequest) {
        setAdminAuthTokens(data.data);
      } else {
        setAuthTokens(data.data);
      }
    }

    // Return any valid JSON response (success or business error like 40400/42200).
    // The backend wraps all responses — including errors — in { code, message, data }.
    if (data) {
      return data as ApiResponse<T>;
    }
  } catch {
    // Network error — backend completely unreachable, fall back to robust mock logic
  }

  return handleMockFallback<T>(endpoint, options);
}

// Full Mock Route Handling Engine for offline/prototype mode
function handleMockFallback<T>(endpoint: string, options: RequestInit): ApiResponse<T> {
  const db = getMockDB();
  const method = (options.method || 'GET').toUpperCase();
  const [path, queryString] = endpoint.split('?');
  const params = new URLSearchParams(queryString || '');
  let body: any = {};
  if (options.body && typeof options.body === 'string') {
    try { body = JSON.parse(options.body); } catch {}
  }

  // 认证关键路径：测试生产阶段不再允许 mock 伪造成功，
  // 后端不可达时明确报错，避免出现“登录成功”但实际未认证的假象。
  const AUTH_REAL_PATHS = [
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/email-register',
    '/api/auth/phone-login',
    '/api/auth/send-code',
    '/api/auth/refresh',
    '/api/admin/login',
    '/api/admin/me',
    '/api/users/me',
  ];
  if (AUTH_REAL_PATHS.includes(path)) {
    return {
      code: -1,
      message: '后端服务不可用，请确认后端已启动后重试',
      data: null as any,
    };
  }

  // Items: List
  if (path === '/api/items' && method === 'GET') {
    let items = [...db.items];
    const category = params.get('category');
    const keyword = params.get('keyword');
    if (category && category !== '全部') {
      items = items.filter((i: ItemOut) => i.category === category);
    }
    if (keyword) {
      items = items.filter((i: ItemOut) => i.title.includes(keyword) || i.description.includes(keyword));
    }
    return { code: 0, message: 'ok', data: { total: items.length, items } as any };
  }

  // Items: Categories (mock 兜底，与 FALLBACK_CATEGORIES 对齐)
  if (path === '/api/items/categories' && method === 'GET') {
    return { code: 0, message: 'ok', data: { categories: ['电子数码', '日常用品', '书籍教材', '运动装备', '宿舍好物', '衣帽鞋包', '票券卡券', '其他'] } as any };
  }

  // Jobs: Categories (mock 兜底)
  if (path === '/api/jobs/categories' && method === 'GET') {
    return { code: 0, message: 'ok', data: { categories: ['助教/助管', '家教辅导', '校园代理', '技术开发', '设计剪辑', '活动执行', '文案编辑', '其他'] } as any };
  }

  // Shares: Categories (mock 兜底)
  if (path === '/api/shares/categories' && method === 'GET') {
    return { code: 0, message: 'ok', data: { categories: ['期末复习题', '考研考证', '课件PPT', '实验报告模版', '竞赛真题', '开源代码', '其他'] } as any };
  }

  // Teammates: Categories (mock 兜底)
  if (path === '/api/teams/categories' && method === 'GET') {
    return { code: 0, message: 'ok', data: { categories: ['学术竞赛', '考研考公', '运动健身', '游戏开黑', '旅行逛街', '期末自习', '其他'] } as any };
  }

  // Canteens: Configs (mock 兜底，含学部/餐饮区/类型/学期)
  if (path === '/api/canteens/configs' && method === 'GET') {
    return {
      code: 0,
      message: 'ok',
      data: {
        campuses: ['文理学部', '工学部', '信息学部', '医学部'],
        zones: {
          文理学部: ['梅园', '桂园', '枫园'],
          工学部: ['湖滨', '工学部', '田园'],
          信息学部: ['信息学部', '星园'],
          医学部: ['医学部'],
        },
        types: ['学生大伙食堂', '风味食堂', '教工食堂'],
        semesters: ['2026-2027-1', '2026-2027-2'],
        current_semester: '2026-2027-1',
      } as any,
    };
  }

  // Courses: Departments (mock 兜底，含学部分组)
  if (path === '/api/courses/departments' && method === 'GET') {
    return {
      code: 0,
      message: 'ok',
      data: {
        departments: ['计算机学院', '软件学院', '数学科学学院', '经济管理学院', '外国语学院', '通识教育中心'],
        groups: [],
      } as any,
    };
  }

  // Items: Get detail
  if (path.startsWith('/api/items/') && method === 'GET') {
    const id = path.split('/')[3];
    const item = db.items.find((i: any) => i.id === id) || db.items[0];
    return { code: 0, message: 'ok', data: item as any };
  }

  // Items: Create
  if (path === '/api/items' && method === 'POST') {
    const newItem: ItemOut = {
      id: 'itm-' + Date.now(),
      owner_id: db.currentUser.id,
      owner_nickname: db.currentUser.nickname,
      owner_avatar: db.currentUser.avatar,
      title: body.title,
      description: body.description || '',
      price: body.price,
      category: body.category || '日常用品',
      status: ItemStatus.OnSale,
      images: body.images?.map((img: any, idx: number) => ({ id: 'img-' + Date.now() + '-' + idx, object_key: img.object_key, sort_order: idx })) || [],
      campus: body.campus || '主校区',
      location: body.location || '校内当面交易',
      created_at: new Date().toISOString(),
      views: 1,
      likes: 0,
      favorites_count: 0
    };
    db.items.unshift(newItem);
    saveMockDB(db);
    return { code: 0, message: '物品发布成功', data: newItem as any };
  }

  // Courses: List
  if (path === '/api/courses' && method === 'GET') {
    const keyword = params.get('keyword') || '';
    let courses = [...db.courses];
    if (keyword) {
      courses = courses.filter((c: any) => c.name.includes(keyword) || c.teacher?.includes(keyword) || c.code?.includes(keyword));
    }
    return { code: 0, message: 'ok', data: { total: courses.length, items: courses } as any };
  }

  // Courses: Get
  if (path.startsWith('/api/courses/') && !path.includes('/reviews') && method === 'GET') {
    const id = path.split('/')[3];
    const course = db.courses.find((c: any) => c.id === id) || db.courses[0];
    const reviews = db.courseReviews.filter((r: any) => r.course_id === id);
    return { code: 0, message: 'ok', data: { ...course, reviews } as any };
  }

  // Courses: Reviews list
  if (path.includes('/courses/') && path.includes('/reviews') && method === 'GET') {
    const id = path.split('/')[3];
    const reviews = db.courseReviews.filter((r: any) => r.course_id === id);
    return { code: 0, message: 'ok', data: { total: reviews.length, items: reviews } as any };
  }

  // Courses: Add review
  if (path.includes('/courses/') && path.includes('/reviews') && method === 'POST') {
    const id = path.split('/')[3];
    const newRev: CourseReviewOut = {
      id: 'crev-' + Date.now(),
      course_id: id,
      user_id: db.currentUser.id,
      user_nickname: db.currentUser.nickname,
      user_avatar: db.currentUser.avatar,
      rating: body.rating || 5,
      teacher_rating: body.teacher_rating || 5,
      workload: body.workload || '适中',
      grading_policy: body.grading_policy || '给分较好，看重平时',
      difficulty: 3.5,
      scoring: 4.5,
      content: body.content || '',
      helpful_count: 0,
      likes: 0,
      created_at: new Date().toISOString()
    };
    db.courseReviews.unshift(newRev);
    saveMockDB(db);
    return { code: 0, message: '评课发布成功', data: newRev as any };
  }

  // Canteens: List
  if (path === '/api/canteens' && method === 'GET') {
    return { code: 0, message: 'ok', data: db.canteens as any };
  }

  // Canteens: Get
  if (path.startsWith('/api/canteens/') && !path.includes('/reviews') && method === 'GET') {
    const id = path.split('/')[3];
    const c = db.canteens.find((cant: any) => cant.id === id) || db.canteens[0];
    return { code: 0, message: 'ok', data: c as any };
  }

  // Canteens: Reviews
  if (path.includes('/canteens/') && path.includes('/reviews') && method === 'GET') {
    const canteenId = path.split('/')[3];
    const stallId = params.get('stall_id');
    let reviews = db.canteenReviews.filter((r: any) => r.canteen_id === canteenId);
    if (stallId) {
      reviews = reviews.filter((r: any) => r.stall_id === stallId);
    }
    return { code: 0, message: 'ok', data: { total: reviews.length, items: reviews } as any };
  }

  // Canteens: Add Review
  if (path.includes('/canteens') && path.includes('/reviews') && method === 'POST') {
    const newRev: CanteenReviewOut = {
      id: 'cant-rev-' + Date.now(),
      canteen_id: body.canteen_id || 'cant-1',
      stall_id: body.stall_id || 'stl-1-1',
      dish_name: body.dish_name || '美味佳肴',
      user_id: db.currentUser.id,
      user_nickname: db.currentUser.nickname,
      rating: body.rating || 5,
      price_cents: body.price_cents,
      content: body.content || '',
      created_at: new Date().toISOString()
    };
    db.canteenReviews.unshift(newRev);
    saveMockDB(db);
    return { code: 0, message: '点评发布成功', data: newRev as any };
  }

  // Jobs: List
  if (path === '/api/jobs' && method === 'GET') {
    const keyword = params.get('keyword') || '';
    const category = params.get('category') || '';
    let jobs = [...db.jobs];
    if (keyword) {
      jobs = jobs.filter((j: any) => j.title.includes(keyword) || j.company.includes(keyword));
    }
    if (category && category !== '全部' && category !== '全部岗位') {
      jobs = jobs.filter((j: any) => j.category === category);
    }
    return { code: 0, message: 'ok', data: { total: jobs.length, items: jobs } as any };
  }

  // Jobs: Create
  if (path === '/api/jobs' && method === 'POST') {
    const newJob: JobOut = {
      id: 'job-' + Date.now(),
      poster_id: db.currentUser.id,
      poster_name: db.currentUser.nickname,
      title: body.title,
      description: body.description || '',
      company: body.company || '校内个人',
      salary_cents: body.salary_cents || 2500,
      salary: body.salary_cents || 2500,
      salary_type: body.salary_type || 'hour',
      category: body.category || '家教兼职',
      status: JobStatus.Hiring,
      location: body.location || '校内',
      contact: body.contact || '站内私信',
      requirements: body.requirements || '',
      time_requirement: '协商排班',
      verified: true,
      created_at: '刚刚'
    };
    db.jobs.unshift(newJob);
    saveMockDB(db);
    return { code: 0, message: '兼职岗位发布成功', data: newJob as any };
  }

  // Shares: List
  if (path === '/api/shares' && method === 'GET') {
    const category = params.get('category') || '';
    const keyword = params.get('keyword') || '';
    let shares = [...db.shares];
    if (category && category !== '全部') {
      shares = shares.filter((s: any) => s.category === category);
    }
    if (keyword) {
      shares = shares.filter((s: any) => s.title.includes(keyword) || s.description.includes(keyword));
    }
    return { code: 0, message: 'ok', data: { total: shares.length, items: shares } as any };
  }

  // Shares: Create
  if (path === '/api/shares' && method === 'POST') {
    const newShare: ShareOut = {
      id: 'shr-' + Date.now(),
      owner_id: db.currentUser.id,
      owner_nickname: db.currentUser.nickname,
      title: body.title,
      description: body.description || '',
      file_key: 'shares/file.pdf',
      file_url: body.file_url || 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=800&auto=format&fit=crop&q=80',
      category: body.category || '生活经验',
      downloads: 0,
      file_size: body.file_size || '2.4 MB',
      created_at: '刚刚',
      likes: 0,
      comments_count: 0
    };
    db.shares.unshift(newShare);
    saveMockDB(db);
    return { code: 0, message: '资源分享成功', data: newShare as any };
  }

  // Shares: Comments
  if (path.includes('/shares/') && path.includes('/comments') && method === 'GET') {
    const shareId = path.split('/')[3];
    const comments = (db.shareComments || []).filter((c: any) => c.share_id === shareId);
    return { code: 0, message: 'ok', data: { total: comments.length, items: comments } as any };
  }

  if (path.includes('/shares/') && path.includes('/comments') && method === 'POST') {
    const shareId = path.split('/')[3];
    const newComment: ShareCommentOut = {
      id: 'shrc-' + Date.now(),
      share_id: shareId,
      user_id: db.currentUser.id,
      user_nickname: db.currentUser.nickname,
      content: body.content,
      created_at: '刚刚'
    };
    if (!db.shareComments) db.shareComments = [];
    db.shareComments.push(newComment);
    const targetShare = db.shares.find((s: any) => s.id === shareId);
    if (targetShare) targetShare.comments_count = (targetShare.comments_count || 0) + 1;
    saveMockDB(db);
    return { code: 0, message: '留言成功', data: newComment as any };
  }

  // Teammates: List
  if (path === '/api/teams' && method === 'GET') {
    return { code: 0, message: 'ok', data: { total: db.teams.length, items: db.teams } as any };
  }

  // Teammates: Create
  if (path === '/api/teams' && method === 'POST') {
    const newTeam: TeamOut = {
      id: 'tm-' + Date.now(),
      creator_id: db.currentUser.id,
      creator_nickname: db.currentUser.nickname,
      creator_name: db.currentUser.nickname,
      title: body.title,
      description: body.description || '',
      required_roles: body.required_roles || '全能搭子',
      status: TeamStatus.Recruiting,
      member_count: 1,
      current_members: 1,
      target_count: body.max_members || 4,
      max_members: body.max_members || 4,
      time: '待定',
      location: '校内',
      category: body.category || '组队招募',
      contact_info: body.contact_info || '',
      created_at: '刚刚',
      members: [
        { id: 'tmm-' + Date.now(), team_id: 'tm-' + Date.now(), user_id: db.currentUser.id, user_nickname: db.currentUser.nickname, role: '发起人', status: MemberStatus.Joined }
      ]
    };
    db.teams.unshift(newTeam);
    saveMockDB(db);
    return { code: 0, message: '招募发起成功', data: newTeam as any };
  }

  // Fallback
  return { code: 0, message: 'ok', data: null as any };
}

// -------------------------------------------------------------
// EXPORTED API METHODS
// -------------------------------------------------------------
export const api = {
  // Auth
  auth: {
    login: (account: string, password: string) =>
      request<TokenResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify({ account, password }) }),
    
    phoneLogin: (target: string, code: string) =>
      request<TokenResponse>('/api/auth/phone-login', { method: 'POST', body: JSON.stringify({ target, code }) }),
    
    emailRegister: (email: string, password: string, code: string, nickname?: string) =>
      request<TokenResponse>('/api/auth/email-register', { method: 'POST', body: JSON.stringify({ email, password, code, nickname }) }),

    register: (params: { username: string; password: string; email?: string; phone?: string; nickname?: string }) =>
      request<UserOut>('/api/auth/register', { method: 'POST', body: JSON.stringify(params) }),

    sendCode: (target: string, purpose: 'login' | 'register' | 'email' | 'bind_email' | 'bind_phone', captchaTicket?: string) =>
      request<SendCodeOut>('/api/auth/send-code', { method: 'POST', body: JSON.stringify({ target, purpose, captcha_ticket: captchaTicket }) }),

    // 滑块验证：开启后必须先通过滑块拿到票据，才能请求发送验证码
    captchaConfig: () =>
      request<CaptchaConfig>('/api/auth/captcha/config'),

    captchaSlider: () =>
      request<SliderCaptcha>('/api/auth/captcha/slider'),

    captchaVerify: (token: string, offsetX: number, track: number[][], elapsedMs: number) =>
      request<SliderVerifyResult>('/api/auth/captcha/verify', {
        method: 'POST',
        body: JSON.stringify({ token, offset_x: offsetX, track, elapsed_ms: elapsedMs }),
      }),

    // 极验行为验证：前端拿到验证结果后交服务端做二次校验换票据
    captchaGeetestVerify: (validate: GeetestValidate) =>
      request<SliderVerifyResult>('/api/auth/captcha/geetest/verify', {
        method: 'POST',
        body: JSON.stringify(validate),
      }),

    emailConfig: () =>
      request<EmailRegisterConfig>('/api/auth/email-config'),
    
    logout: () => request<null>('/api/auth/logout', { method: 'POST' }),
    
    getBindings: () => request<BindingsOut>('/api/auth/bindings', {}, true),
    
    bindEmail: (email: string, code: string) =>
      request<null>('/api/auth/bind/email', { method: 'POST', body: JSON.stringify({ email, code }) }),
    
    bindPhone: (phone: string, code: string) =>
      request<null>('/api/auth/bind/phone', { method: 'POST', body: JSON.stringify({ phone, code }) }),
    
    bindOAuth: (provider: 'wechat' | 'qq', code: string, state?: string) =>
      request<null>('/api/auth/bind/oauth', { method: 'POST', body: JSON.stringify({ provider, code, state }) }),
    
    unbindEmail: () => request<null>('/api/auth/unbind/email', { method: 'DELETE' }),
    unbindPhone: () => request<null>('/api/auth/unbind/phone', { method: 'DELETE' }),
    unbindOAuth: (provider: 'wechat' | 'qq') =>
      request<null>('/api/auth/unbind/oauth', { method: 'DELETE', body: JSON.stringify({ provider }) })
  },

  // User
  users: {
    getMe: () => request<UserProfileOut>('/api/users/me'),
    updateMe: (data: Partial<UserProfileOut>) => request<UserProfileOut>('/api/users/me', { method: 'PATCH', body: JSON.stringify(data) }),
    list: (page = 1, page_size = 20) => request<{ total: number; items: UserOut[] }>(`/api/users?page=${page}&page_size=${page_size}`),
    search: (q: string) => request<UserOut[]>(`/api/users/search?q=${encodeURIComponent(q)}`),
    getItems: (userId?: string) => {
      const db = getMockDB();
      const items = db.items.filter((i: any) => !userId || i.owner_id === userId);
      return Promise.resolve({ code: 0, message: 'ok', data: { total: items.length, items } });
    },
    getFavorites: (userId?: string) => {
      const db = getMockDB();
      return Promise.resolve({ code: 0, message: 'ok', data: { total: db.items.length, items: db.items.slice(0, 2) } });
    },
    changePassword: (oldPass: string, newPass: string) => {
      return Promise.resolve({ code: 0, message: '密码修改成功', data: null });
    }
  },

  // Items (二手交易)
  items: {
    list: (params: { keyword?: string; category?: string; status?: number; page?: number; page_size?: number } = {}) => {
      const q = new URLSearchParams();
      if (params.keyword) q.set('keyword', params.keyword);
      if (params.category) q.set('category', params.category);
      if (params.status !== undefined) q.set('status', params.status.toString());
      if (params.page) q.set('page', params.page.toString());
      if (params.page_size) q.set('page_size', params.page_size.toString());
      return request<{ total: number; items: ItemOut[] }>(`/api/items?${q.toString()}`);
    },
    get: (id: string) => request<ItemOut>(`/api/items/${id}`),
    create: (data: ItemCreate) => request<ItemOut>('/api/items', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: ItemUpdate) => request<ItemOut>(`/api/items/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => request<null>(`/api/items/${id}`, { method: 'DELETE' }),
    trade: (id: string) => request<TradeSessionOut>(`/api/items/${id}/trade`, { method: 'POST' }),
    search: (q: string) => request<ItemOut[]>(`/api/items/search?q=${encodeURIComponent(q)}`),
    categories: () => request<{ categories: string[] }>('/api/items/categories')
  },

  // Jobs (兼职)
  jobs: {
    list: (
      params?: string | { keyword?: string; category?: string; page?: number; page_size?: number },
      status?: number,
      page = 1,
      page_size = 20
    ) => {
      const q = new URLSearchParams();
      if (typeof params === 'string') {
        if (params) q.set('keyword', params);
        if (status !== undefined) q.set('status', status.toString());
        q.set('page', page.toString());
        q.set('page_size', page_size.toString());
      } else if (params && typeof params === 'object') {
        if (params.keyword) q.set('keyword', params.keyword);
        if (params.category) q.set('category', params.category);
        if (params.page) q.set('page', params.page.toString());
        if (params.page_size) q.set('page_size', params.page_size.toString());
      }
      return request<{ total: number; items: JobOut[] }>(`/api/jobs?${q.toString()}`);
    },
    create: (data: JobCreate) => request<JobOut>('/api/jobs', { method: 'POST', body: JSON.stringify(data) }),
    apply: (jobId: string, note?: string) => request<JobApplicationOut>(`/api/jobs/${jobId}/apply`, { method: 'POST', body: JSON.stringify({ note }) }),
    applications: (jobId: string) => request<JobApplicationOut[]>(`/api/jobs/${jobId}/applications`),
    categories: () => request<{ categories: string[] }>('/api/jobs/categories')
  },

  // Messages (会话与实时消息)
  messages: {
    conversations: () => request<ConversationOut[]>('/api/messages/conversations'),
    history: (conversationId: string, page = 1, page_size = 50) =>
      request<{ total: number; items: MessageOut[] }>(`/api/messages/conversations/${conversationId}?page=${page}&page_size=${page_size}`),
    read: async (conversationId: string, last_read_message_id?: string) => {
      // Backend returns { marked: number }, frontend expects { success: boolean }
      const res = await request<{ marked: number }>(`/api/messages/conversations/${conversationId}/read`, { method: 'POST', body: JSON.stringify({ last_read_message_id }) });
      if (res.code === 0) {
        return { ...res, data: { success: true } } as ApiResponse<{ success: boolean }>;
      }
      return { ...res, data: { success: false } } as ApiResponse<{ success: boolean }>;
    },
    unread: async () => {
      // Backend returns { unread: number }, frontend expects { unread_count: number }
      // softAuth: 未读数为非关键请求，401 时降级为 0 而不是踢出登录态
      const res = await request<{ unread: number }>('/api/messages/unread', {}, true);
      if (res.code === 0 && res.data) {
        return { ...res, data: { unread_count: res.data.unread ?? 0 } } as ApiResponse<{ unread_count: number }>;
      }
      return res as unknown as ApiResponse<{ unread_count: number }>;
    }
  },

  // Courses (课程评价)
  courses: {
    list: (keyword = '', page = 1, page_size = 20, department = '') =>
      request<{ total: number; items: CourseOut[] }>(
        `/api/courses?keyword=${encodeURIComponent(keyword)}&page=${page}&page_size=${page_size}${department ? `&department=${encodeURIComponent(department)}` : ''}`
      ),
    get: async (id: string) => {
      // Backend returns { course: CourseOut, reviews: CourseReviewOut[] }
      // Flatten to match frontend expectation (course fields + reviews array)
      const res = await request<{ course: CourseOut; reviews: CourseReviewOut[] }>(`/api/courses/${id}`);
      if (res.code === 0 && res.data) {
        return { ...res, data: { ...res.data.course, reviews: res.data.reviews || [] } } as ApiResponse<CourseOut & { reviews: CourseReviewOut[] }>;
      }
      return res as unknown as ApiResponse<CourseOut & { reviews: CourseReviewOut[] }>;
    },
    create: (data: CourseCreate) => request<CourseOut>('/api/courses', { method: 'POST', body: JSON.stringify(data) }),
    departments: () => request<{ departments: string[]; groups: { group: string; departments: string[] }[] }>('/api/courses/departments'),
    getReviews: async (courseId: string) => {
      // Backend has no dedicated reviews list endpoint; reviews come from the detail endpoint
      const res = await request<{ course: CourseOut; reviews: CourseReviewOut[] }>(`/api/courses/${courseId}`);
      if (res.code === 0 && res.data) {
        const reviews = res.data.reviews || [];
        return { ...res, data: { total: reviews.length, items: reviews } } as ApiResponse<{ total: number; items: CourseReviewOut[] }>;
      }
      return { ...res, data: { total: 0, items: [] } } as ApiResponse<{ total: number; items: CourseReviewOut[] }>;
    },
    addReview: (data: { course_id: string; rating: number; content: string; teacher_rating?: number; workload?: string; grading_policy?: string }) =>
      request<CourseReviewOut>(`/api/courses/${data.course_id}/reviews`, { method: 'POST', body: JSON.stringify(data) }),
    likeReview: (courseId: string, reviewId: string) => {
      const db = getMockDB();
      const rev = db.courseReviews.find((r: any) => r.id === reviewId);
      if (rev) {
        rev.helpful_count = (rev.helpful_count || 0) + 1;
        saveMockDB(db);
      }
      return Promise.resolve({ code: 0, message: '点赞成功', data: null });
    },
    review: (courseId: string, rating: number, content: string) =>
      request<CourseReviewOut>(`/api/courses/${courseId}/reviews`, { method: 'POST', body: JSON.stringify({ rating, content }) })
  },

  // Canteens (食堂与菜品)
  canteens: {
    list: (params?: { campus?: string; zone?: string; canteen_type?: string; semester?: string; keyword?: string }) => {
      const q = new URLSearchParams();
      if (params?.campus) q.set('campus', params.campus);
      if (params?.zone) q.set('zone', params.zone);
      if (params?.canteen_type) q.set('canteen_type', params.canteen_type);
      if (params?.semester) q.set('semester', params.semester);
      if (params?.keyword) q.set('keyword', params.keyword);
      return request<CanteenOut[]>(`/api/canteens?${q.toString()}`);
    },
    configs: () => request<CanteenConfig>('/api/canteens/configs'),
    get: (id: string) => request<CanteenOut>(`/api/canteens/${id}`),
    getDish: (dishId: string) => request<DishOut>(`/api/canteens/dishes/${dishId}`),
    getReviews: (canteenId: string, stallId?: string) =>
      request<{ total: number; items: CanteenReviewOut[] }>(`/api/canteens/${canteenId}/reviews${stallId ? `?stall_id=${stallId}` : ''}`),
    addReview: (data: { canteen_id: string; stall_id: string; dish_name: string; rating: number; content: string; price_cents?: number }) =>
      request<CanteenReviewOut>(`/api/canteens/${data.canteen_id}/reviews`, { method: 'POST', body: JSON.stringify(data) }),
    reviewDish: (dishId: string, rating: number, content: string) =>
      request<CanteenReviewOut>(`/api/canteens/dishes/${dishId}/reviews`, { method: 'POST', body: JSON.stringify({ rating, content }) })
  },

  // Jobs block defined earlier (api.jobs)

  // Share (资源共享)
  shares: {
    list: (
      params?: string | { keyword?: string; category?: string; page?: number; page_size?: number },
      page = 1,
      page_size = 20
    ) => {
      const q = new URLSearchParams();
      if (typeof params === 'string') {
        if (params) q.set('category', params);
        q.set('page', page.toString());
        q.set('page_size', page_size.toString());
      } else if (params && typeof params === 'object') {
        if (params.keyword) q.set('keyword', params.keyword);
        if (params.category) q.set('category', params.category);
        if (params.page) q.set('page', params.page.toString());
        if (params.page_size) q.set('page_size', params.page_size.toString());
      }
      return request<{ total: number; items: ShareOut[] }>(`/api/shares?${q.toString()}`);
    },
    create: (data: ShareCreate) => request<ShareOut>('/api/shares', { method: 'POST', body: JSON.stringify(data) }),
    download: async (id: string) => {
      // Backend returns { url: string }, frontend expects { download_url: string }
      const res = await request<{ url: string }>(`/api/shares/${id}/download`);
      if (res.code === 0 && res.data) {
        return { ...res, data: { download_url: res.data.url } } as ApiResponse<{ download_url: string }>;
      }
      return res as unknown as ApiResponse<{ download_url: string }>;
    },
    like: (id: string) => {
      const db = getMockDB();
      const s = db.shares.find((shr: any) => shr.id === id);
      if (s) {
        s.likes = (s.likes || 0) + 1;
        saveMockDB(db);
      }
      return Promise.resolve({ code: 0, message: '点赞成功', data: null });
    },
    getComments: (id: string) =>
      request<{ total: number; items: ShareCommentOut[] }>(`/api/shares/${id}/comments`),
    addComment: (id: string, content: string) =>
      request<ShareCommentOut>(`/api/shares/${id}/comments`, { method: 'POST', body: JSON.stringify({ content }) }),
    categories: () => request<{ categories: string[] }>('/api/shares/categories')
  },

  // Teammates (组队搭子)
  teammates: {
    list: (params?: { category?: string; page?: number; page_size?: number }) =>
      request<{ total: number; items: TeamOut[] }>(
        (() => {
          const q = new URLSearchParams();
          if (params?.category) q.set('category', params.category);
          if (params?.page) q.set('page', params.page.toString());
          if (params?.page_size) q.set('page_size', params.page_size.toString());
          return `/api/teams?${q.toString()}`;
        })()
      ),
    get: async (id: string) => {
      // Backend returns { team: TeamOut, members: TeamMemberOut[] }
      // Flatten to match frontend expectation (team fields + members array)
      const res = await request<{ team: TeamOut; members: TeamMemberOut[] }>(`/api/teams/${id}`);
      if (res.code === 0 && res.data) {
        return { ...res, data: { ...res.data.team, members: res.data.members || [] } } as ApiResponse<TeamOut>;
      }
      return res as unknown as ApiResponse<TeamOut>;
    },
    create: (data: TeamCreate) => request<TeamOut>('/api/teams', { method: 'POST', body: JSON.stringify(data) }),
    join: (teamId: string, role?: string) => request<TeamMemberOut>(`/api/teams/${teamId}/join`, { method: 'POST', body: JSON.stringify({ role }) }),
    apply: (teamId: string, note: string) => {
      return Promise.resolve({ code: 0, message: '申请成功', data: null });
    },
    close: (teamId: string) => {
      const db = getMockDB();
      const t = db.teams.find((tm: any) => tm.id === teamId);
      if (t) {
        t.status = TeamStatus.Closed;
        saveMockDB(db);
      }
      return Promise.resolve({ code: 0, message: '已关闭招募', data: null });
    },
    categories: () => request<{ categories: string[] }>('/api/teams/categories')
  },

  // Reports (举报投诉)
  reports: {
    submit: (target_type: ReportTargetType, target_id: string, reason: string) =>
      request<ReportOut>('/api/reports', { method: 'POST', body: JSON.stringify({ target_type, target_id, reason }) }),
    list: (status?: number, page = 1, page_size = 20) => {
      const q = new URLSearchParams();
      if (status !== undefined) q.set('status', status.toString());
      q.set('page', page.toString());
      q.set('page_size', page_size.toString());
      return request<{ total: number; items: ReportOut[] }>(`/api/reports?${q.toString()}`);
    },
    handle: (reportId: string, action: 'resolve' | 'reject' | 'ban', note?: string) =>
      request<ReportOut>(`/api/reports/${reportId}/handle`, { method: 'POST', body: JSON.stringify({ action, note }) })
  },

  // Admin
  admin: {
    // 用网关密钥换取短时网关令牌（HMAC），缓存后由 request() 自动附带
    discover: (gatewayKey: string) =>
      request<{ gateway_token: string }>('/api/admin/discover', { method: 'POST', body: JSON.stringify({ gateway_key: gatewayKey }) }),
    // 先 discover 换取网关令牌再登录，成功后缓存令牌
    loginWithGateway: async (gatewayKey: string, username: string, password: string) => {
      const d = await api.admin.discover(gatewayKey);
      if (d.code === 0 && d.data?.gateway_token) {
        setAdminGatewayToken(d.data.gateway_token);
        return api.admin.login(username, password);
      }
      // 网关密钥错误或后台未开放管理端：返回友好错误（后端对未授权访问统一 404 屏蔽）
      return { code: 40100, message: '管理后台网关密钥错误或未开放', data: null } as unknown as ApiResponse<TokenResponse>;
    },
    login: (username: string, password: string) =>
      request<TokenResponse>('/api/admin/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
    getMe: () => request<AdminOut>('/api/admin/me'),
    dashboard: () => request<any>('/api/admin/dashboard'),
    getOverview: () => api.admin.dashboard(),
    getReports: (status?: number) => api.admin.reports(status),
    // 审计日志：真实后端接口（记录登录/注册/发送验证码/管理员操作等全量动作）
    getLogs: (params: {
      action?: string;
      actor_type?: string;
      result?: string;
      keyword?: string;
      limit?: number;
      offset?: number;
    } = {}) => {
      const q = new URLSearchParams();
      if (params.action) q.set('action', params.action);
      if (params.actor_type) q.set('actor_type', params.actor_type);
      if (params.result) q.set('result', params.result);
      if (params.keyword) q.set('keyword', params.keyword);
      if (params.limit) q.set('limit', String(params.limit));
      if (params.offset) q.set('offset', String(params.offset));
      const qs = q.toString();
      return request<{ total: number; items: any[]; limit: number; offset: number }>(
        `/api/admin/audit-logs${qs ? `?${qs}` : ''}`
      );
    },
    getAuditActions: () =>
      request<{ value: string; label: string }[]>('/api/admin/audit-logs/actions'),
    getUsers: (page = 1, page_size = 20) => api.admin.users(page, page_size),
    handleReport: (reportId: string, data: { status: number; action: any; feedback: string }) =>
      api.reports.handle(reportId, data.action, data.feedback),
    updateUserStatus: (userId: string, status: number) =>
      status === 1 ? api.admin.banUser(userId) : api.admin.unbanUser(userId),
    users: (page = 1, page_size = 20) => request<{ total: number; items: any[] }>(`/api/admin/users?page=${page}&page_size=${page_size}`),
    banUser: (userId: string, reason = '') => request<any>(`/api/admin/users/${userId}/ban`, { method: 'POST', body: JSON.stringify({ reason }) }),
    unbanUser: (userId: string) => request<any>(`/api/admin/users/${userId}/unban`, { method: 'POST' }),
    getEmailConfig: () => request<EmailRegisterConfig>('/api/admin/auth/email-config'),
    updateEmailConfig: (config: EmailRegisterConfig) => request<EmailRegisterConfig>('/api/admin/auth/email-config', { method: 'PUT', body: JSON.stringify(config) }),
    reports: (status?: number, page = 1, page_size = 20) => request<{ total: number; items: ReportOut[] }>(`/api/admin/reports?status=${status || ''}&page=${page}&page_size=${page_size}`),
    // Admin item management (bypasses owner checks)
    adminItems: (status?: number, page = 1, page_size = 20) =>
      request<{ total: number; items: any[] }>(`/api/admin/items?status=${status ?? ''}&page=${page}&page_size=${page_size}`),
    adminUpdateItem: (itemId: string, data: { status?: number; title?: string; description?: string; price?: number; category?: string }) =>
      request<any>(`/api/admin/items/${itemId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    adminDeleteItem: (itemId: string) =>
      request<any>(`/api/admin/items/${itemId}`, { method: 'DELETE' }),
    getItemReviewConfig: () => request<ItemReviewConfig>('/api/admin/items/review-config'),
    updateItemReviewConfig: (config: ItemReviewConfig) =>
      request<ItemReviewConfig>('/api/admin/items/review-config', { method: 'PUT', body: JSON.stringify(config) }),
    getItemCategories: () => request<{ categories: string[] }>('/api/admin/items/categories'),
    updateItemCategories: (categories: string[]) =>
      request<{ categories: string[] }>('/api/admin/items/categories', { method: 'PUT', body: JSON.stringify({ categories }) }),
    getCourseDepartments: () => request<{ departments: string[] }>('/api/admin/courses/departments'),
    updateCourseDepartments: (departments: string[]) =>
      request<{ departments: string[] }>('/api/admin/courses/departments', { method: 'PUT', body: JSON.stringify({ departments }) }),
    // Storage maintenance (orphan files)
    listOrphanFiles: () => request<{ files: { key: string; size: number }[]; total: number }>('/api/admin/files/orphans', { method: 'GET' }),
    cleanupOrphanFiles: () => request<{ removed: number }>('/api/admin/files/orphans', { method: 'DELETE' }),
    // Canteen management (admin-only CRUD)
    canteens: {
      list: () => request<CanteenOut[]>('/api/admin/canteens'),
      create: (data: { name: string; location: string; image?: string }) =>
        request<CanteenOut>('/api/admin/canteens', { method: 'POST', body: JSON.stringify(data) }),
      update: (id: string, data: { name: string; location: string; image?: string }) =>
        request<CanteenOut>(`/api/admin/canteens/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
      remove: (id: string) => request<null>(`/api/admin/canteens/${id}`, { method: 'DELETE' }),
      createStall: (data: { canteen_id: string; name: string; image?: string }) =>
        request<StallOut>('/api/admin/canteens/stalls', { method: 'POST', body: JSON.stringify(data) }),
      updateStall: (id: string, data: { canteen_id: string; name: string; image?: string }) =>
        request<StallOut>(`/api/admin/canteens/stalls/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
      removeStall: (id: string) => request<null>(`/api/admin/canteens/stalls/${id}`, { method: 'DELETE' }),
      createDish: (data: { stall_id: string; name: string; price: number; image?: string }) =>
        request<DishOut>('/api/admin/canteens/dishes', { method: 'POST', body: JSON.stringify(data) }),
      updateDish: (id: string, data: { stall_id: string; name: string; price: number; image?: string }) =>
        request<DishOut>(`/api/admin/canteens/dishes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
      removeDish: (id: string) => request<null>(`/api/admin/canteens/dishes/${id}`, { method: 'DELETE' })
    },
    approveItem: (itemId: string) =>
      request<any>(`/api/admin/items/${itemId}/approve`, { method: 'POST' }),
    rejectItem: (itemId: string, reason = '') =>
      request<any>(`/api/admin/items/${itemId}/reject`, { method: 'POST', body: JSON.stringify({ reason }) }),
    // AI 助手配置
    getAiConfig: () => request<AiConfig>('/api/admin/ai/config'),
    updateAiConfig: (config: AiConfigUpdate) =>
      request<AiFeatureConfig>('/api/admin/ai/config', { method: 'PUT', body: JSON.stringify(config) })
  },

  // AI 智能助手（Gemini）
  ai: {
    status: () => request<AiStatusOut>('/api/ai/status'),
    getInsights: (topic: string) =>
      request<{ text: string }>('/api/ai/insights', { method: 'POST', body: JSON.stringify({ topic }) }),
    generateItemDescription: (title: string, category: string) =>
      request<{ text: string }>('/api/ai/item-description', { method: 'POST', body: JSON.stringify({ title, category }) }),
    summarizeCourseReviews: (reviewTexts: string[]) =>
      request<{ text: string }>('/api/ai/course-summary', { method: 'POST', body: JSON.stringify({ reviewTexts }) }),
    categorizePost: (content: string) =>
      request<{ category: string; isSafe: boolean; summary: string }>('/api/ai/categorize', { method: 'POST', body: JSON.stringify({ content }) }),
    // AI 配置（管理端路由 /api/admin/ai/config，需管理员权限，与 admin.* 同一后端）
    getConfig: () => request<AiConfig>('/api/admin/ai/config'),
    updateConfig: (config: AiConfigUpdate) =>
      request<AiFeatureConfig>('/api/admin/ai/config', { method: 'PUT', body: JSON.stringify(config) })
  },

  // Files
  files: {
    presign: async (prefix = 'misc', filename = 'file.bin') => {
      return request<{ object_key: string; upload_url: string; direct: boolean }>('/api/files/presign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ prefix, filename }).toString()
      });
    },
    upload: async (key: string, file: File) => {
      const formData = new FormData();
      formData.append('key', key);
      formData.append('file', file);
      const token = getStoredAccessToken();
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch('/api/files/upload', { method: 'POST', headers, body: formData });
      return await res.json();
    },
    /**
     * High-level upload helper: presign + upload.
     *
     * - If `direct` is true (MinIO enabled): PUT the file directly to the
     *   presigned MinIO URL.
     * - If `direct` is false (local fallback): POST multipart form data to
     *   `/api/files/upload`.
     *
     * Returns the `object_key` which can be used in `ItemCreate.images`.
     */
    uploadImage: async (file: File, prefix = 'items'): Promise<string> => {
      const presignRes = await api.files.presign(prefix, file.name);
      if (presignRes.code !== 0 || !presignRes.data) {
        throw new Error(presignRes.message || 'Presign failed');
      }
      const { object_key, upload_url, direct } = presignRes.data;
      if (direct) {
        // MinIO mode: PUT directly to the presigned URL (no auth header needed)
        const putRes = await fetch(upload_url, {
          method: 'PUT',
          body: file,
          headers: { 'Content-Type': file.type || 'application/octet-stream' }
        });
        if (!putRes.ok) {
          throw new Error(`Direct upload failed: ${putRes.status}`);
        }
      } else {
        // Local fallback: POST multipart to /api/files/upload
        const uploadRes = await api.files.upload(object_key, file);
        if (uploadRes.code !== 0) {
          throw new Error(uploadRes.message || 'Local upload failed');
        }
      }
      return object_key;
    }
  }
};
