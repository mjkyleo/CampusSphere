# -*- coding: utf-8 -*-
"""灌入 15 个测试用户（user01~user15 / 123456）的全功能真实数据。

覆盖：二手交易（发布/预订/成交/取消）、课程+评价、食堂档口菜品+评价、
兼职+申请、资料分享+点赞、组队+队员、IM 会话+消息、举报工单+处理日志。

用法：cd backend && python scripts/seed_full_data.py
幂等：检测到已有数据时退出（不重复灌入）；如需重灌，先删除 dev.db 并重启后端。
说明：直接走 ORM 灌库（非 HTTP API），避免认证限流；数据合法性与 seed_demo_users.py 一致。
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select  # noqa: E402

from app.common.enums import (  # noqa: E402
    ApplicationStatus,
    ItemStatus,
    JobStatus,
    MemberStatus,
    ReportStatus,
    ReportTargetType,
    TeamStatus,
    TradeStatus,
    UserStatus,
)
from app.core.database import SessionLocal  # noqa: E402
from app.modules.auth.models import User  # noqa: E402
from app.modules.canteen.models import Canteen, CanteenReview, Dish, Stall  # noqa: E402
from app.modules.course.models import Course, CourseReview  # noqa: E402
from app.modules.item.models import Item, TradeSession  # noqa: E402
from app.modules.job.models import Job, JobApplication  # noqa: E402
from app.modules.message.models import Conversation, Message, Participant  # noqa: E402
from app.modules.report.models import Report, ReportLog  # noqa: E402
from app.modules.share.models import ShareResource  # noqa: E402
from app.modules.teammate.models import Team, TeamMember  # noqa: E402

NICKnames = [
    "沐辰", "知夏", "子轩", "雨桐", "思远", "若溪", "宇航", "欣怡",
    "浩然", "诗涵", "嘉懿", "语嫣", "泽宇", "婉清", "明哲",
]


async def main() -> None:
    async with SessionLocal() as db:
        # 幂等检查：items 表有数据即视为已灌入
        if (await db.scalar(select(func.count()).select_from(Item))) > 0:
            print("[skip] 业务数据已存在，退出。如需重灌请删除 dev.db 并重启后端。")
            return

        # ---------- 15 个用户（复用已存在的 API 创建的用户，补邮箱/昵称） ----------
        existing = (await db.scalars(select(User))).all()
        by_name = {u.username: u for u in existing}
        users: dict[str, User] = {}
        for i in range(1, 16):
            name = f"user{i:02d}"
            u = by_name.get(name)
            if u is None:
                u = User(username=name, status=UserStatus.NORMAL.value, is_admin=False)
                db.add(u)
            u.email = f"{name}@whu.edu.cn"
            u.nickname = NICKnames[i - 1]
            u.status = UserStatus.NORMAL.value
            u.set_password("123456")
            users[name] = u
        await db.flush()
        print(f"[users] {len(users)} 个用户就绪（user01~user15 / 123456）")

        # ---------- 二手交易 ----------
        item_specs = [
            ("user01", "九成新 AirPods 耳机", "自用半年，续航正常，无划痕", 39900, "电子产品", ItemStatus.ON_SALE),
            ("user01", "高数（上）教材+习题册", "张宇高数上下全套，附笔记", 2500, "书籍资料", ItemStatus.SOLD),
            ("user02", "捷安特山地自行车", "毕业出，链条刚保养过", 80000, "交通工具", ItemStatus.ON_SALE),
            ("user02", "宿舍护眼台灯", "三档调光，几乎全新", 4500, "日用百货", ItemStatus.RESERVED),
            ("user03", "考研数学真题解析", "2009-2024 全套，满页笔记", 3000, "书籍资料", ItemStatus.ON_SALE),
            ("user03", "斯伯丁篮球 7 号", "室内外通用，8 成新", 6000, "运动户外", ItemStatus.OFF_SHELF),
            ("user04", "秋冬针织连衣裙", "全新未拆吊牌，M 码", 8900, "美妆服饰", ItemStatus.ON_SALE),
            ("user05", "机械键盘 Cherry 轴", "青轴，键帽已换，手感清脆", 22000, "电子产品", ItemStatus.ON_SALE),
            ("user06", "校园二手电动车", "续航 40 公里，含充电器", 120000, "交通工具", ItemStatus.ON_SALE),
            ("user07", "雅思红宝书", "最新版，只用过一次", 3500, "书籍资料", ItemStatus.ON_SALE),
            ("user08", "单反相机 Canon 200D", "含 18-55 镜头，快门数 3000", 280000, "电子产品", ItemStatus.ON_SALE),
            ("user09", "折叠自行车", "小巧便携，地铁通勤神器", 45000, "交通工具", ItemStatus.ON_SALE),
            ("user10", "宿舍小冰箱", "50L，制冷正常，毕业转让", 30000, "日用百货", ItemStatus.ON_SALE),
        ]
        items: dict[str, Item] = {}
        for owner, title, desc, price, cat, status in item_specs:
            it = Item(owner_id=users[owner].id, title=title, description=desc,
                      price=price, category=cat, status=status.value)
            db.add(it)
            items[title] = it
        await db.flush()

        trade_specs = [
            (items["高数（上）教材+习题册"], "user05", "user01", TradeStatus.COMPLETED),
            (items["宿舍护眼台灯"], "user06", "user02", TradeStatus.IN_PROGRESS),
            (items["九成新 AirPods 耳机"], "user11", "user01", TradeStatus.PENDING),
            (items["机械键盘 Cherry 轴"], "user12", "user05", TradeStatus.PENDING),
        ]
        trades: dict[str, TradeSession] = {}
        for it, buyer, seller, status in trade_specs:
            ts = TradeSession(item_id=it.id, buyer_id=users[buyer].id,
                              seller_id=users[seller].id, status=status.value)
            db.add(ts)
            trades[it.title] = ts
        await db.flush()
        print(f"[items] {len(items)} 件物品，{len(trades)} 个交易会话")

        # ---------- 课程 + 评价 ----------
        course_specs = [
            ("CS201", "数据结构", "张伟", 3, "2026-2027-1", "计算机学院"),
            ("MATH101", "微积分（一）", "李建国", 5, "2026-2027-1", "数学与统计学院"),
            ("PHY101", "大学物理（上）", "王强", 4, "2026-2027-1", "物理科学与技术学院"),
            ("ECON101", "微观经济学", "陈静", 3, "2026-2027-1", "经济与管理学院"),
            ("ENG201", "大学英语（三）", "刘芳", 2, "2026-2027-1", "外国语言文学学院"),
            ("AI101", "人工智能导论", "周明", 2, "2026-2027-1", "通识教育中心"),
            ("CS301", "操作系统", "赵鹏", 4, "2026-2027-1", "计算机学院"),
            ("LAW101", "法律基础", "孙丽", 2, "2026-2027-1", "法学院"),
        ]
        courses: dict[str, Course] = {}
        for code, name, teacher, credits, sem, dept in course_specs:
            c = Course(code=code, name=name, teacher=teacher, credits=credits,
                       semester=sem, department=dept)
            db.add(c)
            courses[name] = c
        await db.flush()

        review_specs = [
            ("user05", "数据结构", 5, "张老师板书清晰，作业量适中，期末有重点串讲，给分很友好。"),
            ("user06", "数据结构", 4, "课程安排合理，实验稍多但收获很大。"),
            ("user07", "微积分（一）", 5, "内容扎实，讲得很细，想拿高分需要多刷题。"),
            ("user08", "大学物理（上）", 5, "王老师讲得生动，实验课有趣，强烈推荐。"),
            ("user09", "微观经济学", 4, "案例丰富，理论与实际结合得很好。"),
            ("user10", "大学英语（三）", 3, "课堂互动多，但考核偏口语，内向同学要提前准备。"),
            ("user11", "人工智能导论", 5, "前沿内容多，项目实战很有价值。"),
            ("user12", "操作系统", 4, "难度较大但讲得透彻，实验设计很好。"),
            ("user13", "法律基础", 5, "老师风趣幽默，案例贴近生活。"),
        ]
        for uid, cname, rating, content in review_specs:
            db.add(CourseReview(course_id=courses[cname].id, user_id=users[uid].id,
                                rating=rating, content=content))
        await db.flush()
        print(f"[course] {len(courses)} 门课程，{len(review_specs)} 条评价")

        # ---------- 食堂：档口/菜品/评价 ----------
        canteens = {c.name: c for c in (await db.scalars(select(Canteen))).all()}
        if not canteens:
            for name, campus, zone in [("梅园食堂", "文理学部", "梅园"),
                                        ("工学部食堂", "工学部", "工学部"),
                                        ("信息学部食堂", "信息学部", "信息学部")]:
                c = Canteen(name=name, campus=campus, zone=zone, location=campus)
                db.add(c)
                canteens[name] = c
            await db.flush()
        stall_specs = [
            ("梅园食堂", "热干面窗口", [("热干面", 600), ("三鲜豆皮", 800), ("糊汤粉", 700)]),
            ("梅园食堂", "盖浇饭窗口", [("鱼香肉丝饭", 1200), ("宫保鸡丁饭", 1200)]),
            ("工学部食堂", "铁板饭窗口", [("铁板鸡排饭", 1500), ("铁板牛肉饭", 1800)]),
            ("工学部食堂", "麻辣烫窗口", [("麻辣烫（份）", 1300)]),
            ("信息学部食堂", "黄焖鸡窗口", [("黄焖鸡米饭", 1500), ("红烧牛肉粉", 1200)]),
        ]
        dishes: dict[str, Dish] = {}
        for cname, sname, dish_list in stall_specs:
            st = Stall(canteen_id=canteens[cname].id, name=sname)
            db.add(st)
            await db.flush()
            for dname, price in dish_list:
                d = Dish(stall_id=st.id, name=dname, price=price)
                db.add(d)
                dishes[dname] = d
        await db.flush()
        dish_reviews = [
            ("user08", "热干面", 5, "芝麻酱香浓，面条筋道，早八必点！"),
            ("user09", "黄焖鸡米饭", 4, "鸡肉入味，汤汁拌饭绝了，就是量有点少。"),
            ("user10", "麻辣烫（份）", 4, "食材新鲜，汤底可选，微辣刚好。"),
            ("user11", "红烧牛肉粉", 5, "牛肉给得多，汤头浓郁，回购多次。"),
            ("user12", "铁板鸡排饭", 4, "分量足，洋葱打底很香。"),
            ("user13", "三鲜豆皮", 5, "外皮酥脆内馅饱满，武汉老味道。"),
            ("user14", "鱼香肉丝饭", 4, "味道不错，出餐快。"),
            ("user15", "糊汤粉", 5, "地道武汉早餐，配油条一绝。"),
        ]
        for uid, dname, rating, content in dish_reviews:
            db.add(CanteenReview(dish_id=dishes[dname].id, user_id=users[uid].id,
                                 rating=rating, content=content))
        await db.flush()
        print(f"[canteen] {len(stall_specs)} 档口，{len(dishes)} 菜品，{len(dish_reviews)} 评价")

        # ---------- 兼职 + 申请 ----------
        job_specs = [
            ("user02", "图书馆自习区管理员助理", "整理书架、维护自习秩序，每周 3 个班次", "校图书馆", 15000, 1, "助教/助管", "图书馆一楼服务台", "微信：lib_helper", "每周至少 3 个晚班，细致耐心"),
            ("user02", "初二数学家教", "每周六下午 2 小时，上门辅导", "家教中心", 20000, 0, "家教辅导", "校内东区 / 线上", "微信：math_tutor_02", "初二数学基础薄弱学生，需有家教经验"),
            ("user03", "校园咖啡品牌代理", "负责校内推广与团购配送", "某咖啡品牌", 12000, 3, "校园代理", "校内各宿舍区", "微信：campus_coffee", "熟悉校园社群，有推广经验优先"),
            ("user04", "实验室助理招聘", "协助实验准备与数据记录", "化学学院", 18000, 1, "助教/助管", "化学楼 301", "邮箱：chem_lab@example.edu.cn", "化学相关专业，实验操作规范"),
            ("user05", "校报排版志愿者", "负责校报排版与校对", "校报编辑部", 8000, 3, "其他", "校报编辑部办公室", "微信：campus_paper", "熟悉 InDesign 或方正排版"),
        ]
        jobs: dict[str, Job] = {}
        for poster, title, desc, comp, salary, salary_type, cat, location, contact, requirements in job_specs:
            j = Job(poster_id=users[poster].id, title=title, description=desc,
                    company=comp, salary=salary, salary_type=salary_type, category=cat,
                    location=location, contact=contact, requirements=requirements,
                    status=JobStatus.OPEN.value)
            db.add(j)
            jobs[title] = j
        await db.flush()
        app_specs = [
            ("user06", "图书馆自习区管理员助理", "可以安排每周一二四晚班"),
            ("user07", "初二数学家教", "有两年家教经验，附简历"),
            ("user08", "校园咖啡品牌代理", "对校内渠道熟悉"),
            ("user09", "实验室助理招聘", "化学专业，实验经验丰富"),
            ("user10", "校报排版志愿者", "熟悉 InDesign 排版"),
            ("user11", "图书馆自习区管理员助理", "时间灵活，随时可排班"),
        ]
        for uid, jtitle, note in app_specs:
            db.add(JobApplication(job_id=jobs[jtitle].id, applicant_id=users[uid].id,
                                  status=ApplicationStatus.PENDING.value, note=note))
        await db.flush()
        print(f"[job] {len(jobs)} 岗位，{len(app_specs)} 申请")

        # ---------- 资源共享 ----------
        share_specs = [
            ("user06", "高数（上）期末真题+答案", "近五年真题整理，附手写解析", "期末复习题", 32, "https://www.bing.com/search?q=高等数学+期末真题", ["高数", "真题"]),
            ("user06", "考研英语真题词汇笔记", "历年真题高频词汇整理，配合例句", "考研考证", 18, "https://www.bing.com/search?q=考研英语+真题+词汇", ["考研", "英语"]),
            ("user07", "课程设计报告模板", "含目录/图表/参考文献格式，可直接套用", "实验报告模版", 45, "https://www.bing.com/search?q=课程设计报告+模板", ["模板", "报告"]),
            ("user08", "Python 爬虫开源代码", "校园公开数据爬取示例，含反爬说明", "开源代码", 27, "https://github.com/search?q=python+crawler", ["Python", "开源"]),
            ("user09", "C++ STL 速查手册", "常用容器与算法整理", "期末复习题", 56, "https://www.bing.com/search?q=C%2B%2B+STL+速查", ["C++", "算法"]),
            ("user10", "雅思口语话题模板", "Part1/2/3 高频话题", "考研考证", 21, "https://www.bing.com/search?q=雅思口语+话题+模板", ["雅思", "口语"]),
        ]
        for owner, title, desc, cat, dls, url, tags in share_specs:
            db.add(ShareResource(owner_id=users[owner].id, title=title,
                                 description=desc, category=cat, downloads=dls,
                                 file_url=url, tags=json.dumps(tags, ensure_ascii=False)))
        await db.flush()
        print(f"[share] {len(share_specs)} 份资料")

        # ---------- 组队 ----------
        team_specs = [
            ("user08", "数学建模国赛 3 缺 1", "C 题方向，缺一名建模手/论文手", "建模手/论文手", "学术竞赛", 4),
            ("user09", "东湖夜跑搭子", "每周二四六晚 8 点，配速 6 分半", "跑友", "运动健身", 6),
            ("user10", "考研自习搭子", "图书馆 4 楼固定座位，互相监督打卡", "研友", "考研考公", 4),
            ("user11", "篮球 3v3 组队", "周末下午打全场，缺 2 人", "后卫/前锋", "运动健身", 5),
        ]
        teams: dict[str, Team] = {}
        for creator, title, desc, roles, cat, mx in team_specs:
            t = Team(creator_id=users[creator].id, title=title, description=desc,
                     required_roles=roles, status=TeamStatus.RECRUITING.value,
                     category=cat, max_members=mx, contact_info="站内私信")
            db.add(t)
            teams[title] = t
        await db.flush()
        member_specs = [
            ("user01", "数学建模国赛 3 缺 1", "建模手"),
            ("user02", "数学建模国赛 3 缺 1", "论文手"),
            ("user03", "东湖夜跑搭子", "跑友"),
            ("user04", "考研自习搭子", "研友"),
            ("user12", "篮球 3v3 组队", "后卫"),
            ("user13", "篮球 3v3 组队", "前锋"),
        ]
        for uid, ttitle, role in member_specs:
            db.add(TeamMember(team_id=teams[ttitle].id, user_id=users[uid].id,
                              role=role, status=MemberStatus.PENDING.value))
        await db.flush()
        print(f"[team] {len(teams)} 队伍，{len(member_specs)} 入队记录")

        # ---------- 会话 + 消息 ----------
        conv_specs = [
            ("trade", trades["高数（上）教材+习题册"].id, ["user05", "user01"],
             [("user05", "同学你好，高数教材还在吗？"), ("user01", "在的，九成新，附全套笔记"),
              ("user05", "我诚心要，校内哪里面交？"), ("user01", "图书馆门口，随时"),
              ("user05", "好，那就约今天下午")]),
            ("trade", trades["宿舍护眼台灯"].id, ["user06", "user02"],
             [("user06", "台灯还能便宜点吗？"), ("user02", "最低 40 了，基本全新"),
              ("user06", "行，周末当面验货")]),
            ("direct", None, ["user08", "user09"],
             [("user08", "周六晚上东湖夜跑约吗？"), ("user09", "约！老时间老地方")]),
            ("direct", None, ["user01", "user05"],
             [("user05", "耳机 350 能不能出？"), ("user01", "可以小刀，380 最低")]),
            ("direct", None, ["user10", "user11"],
             [("user10", "考研搭子还缺人吗？"), ("user11", "还缺一个，来吗？")]),
        ]
        msg_count = 0
        for conv_type, related_id, part_names, msgs in conv_specs:
            conv = Conversation(conv_type=conv_type, related_id=related_id)
            db.add(conv)
            await db.flush()
            for pn in part_names:
                db.add(Participant(conversation_id=str(conv.id), user_id=users[pn].id))
            for sender, content in msgs:
                db.add(Message(conversation_id=str(conv.id), sender_id=users[sender].id,
                               type=0, content=content, is_read=True))
                msg_count += 1
        await db.flush()
        print(f"[message] {len(conv_specs)} 会话，{msg_count} 条消息")

        # ---------- 举报 ----------
        report_specs = [
            ("user03", ReportTargetType.ITEM, items["九成新 AirPods 耳机"].id,
             "怀疑为高仿耳机，卖家描述与实物不符", ReportStatus.PENDING, None),
            ("user04", ReportTargetType.USER, users["user03"].id,
             "该用户发布的兼职信息疑似虚假引流", ReportStatus.PENDING, None),
            ("user05", ReportTargetType.SHARE, None,
             "上传内容疑似抄袭他人课程设计", ReportStatus.RESOLVED, "resolve"),
            ("user06", ReportTargetType.COMMENT, None,
             "评论内容恶意攻击授课教师", ReportStatus.REJECTED, "reject"),
            ("user07", ReportTargetType.ITEM, items["捷安特山地自行车"].id,
             "价格异常偏低，疑似诈骗", ReportStatus.PENDING, None),
        ]
        share_target = (await db.scalars(select(ShareResource))).all()[0]
        review_target = (await db.scalars(select(CourseReview))).all()[0]
        report_specs[2] = (*report_specs[2][:2], share_target.id, *report_specs[2][3:])
        report_specs[3] = (*report_specs[3][:2], review_target.id, *report_specs[3][3:])
        for reporter, ttype, tid, reason, status, action in report_specs:
            rp = Report(reporter_id=users[reporter].id, target_type=ttype.value,
                        target_id=tid, reason=reason, status=status.value)
            db.add(rp)
            await db.flush()
            if action:
                db.add(ReportLog(report_id=str(rp.id), action=action,
                                 note="已核实处理" if action == "resolve" else "证据不足，驳回"))
        await db.commit()
        print(f"[report] {len(report_specs)} 条举报工单")
        print("\n=== 完成：15 用户全功能数据已灌入（二手/课程/食堂/兼职/分享/组队/消息/举报） ===")


if __name__ == "__main__":
    asyncio.run(main())
