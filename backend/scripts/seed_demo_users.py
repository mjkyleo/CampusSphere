# -*- coding: utf-8 -*-
"""灌入 10 个演示用户（user01~user10，密码统一 123456）及全功能使用记录。

覆盖功能：二手交易（发布/议价会话）、课程评价、食堂（档口/菜品/评价）、
兼职（发布/申请）、资源共享、队友招募、即时消息、举报工单。

用法：py -3 scripts/seed_demo_users.py
重复执行安全：user01 已以演示昵称存在时直接退出，避免重复灌入。
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from app.common.enums import (
    ApplicationStatus,
    ItemStatus,
    JobStatus,
    MemberStatus,
    MessageType,
    ReportStatus,
    ReportTargetType,
    TeamStatus,
    TradeStatus,
    UserStatus,
)
from app.core.database import SessionLocal
from app.modules.auth.models import User
from app.modules.canteen.models import Canteen, CanteenReview, Dish, Stall
from app.modules.course.models import Course, CourseReview
from app.modules.item.models import Item, TradeSession
from app.modules.job.models import Job, JobApplication
from app.modules.message.models import Conversation, Message, Participant
from app.modules.report.models import Report, ReportLog
from app.modules.share.models import ShareResource
from app.modules.teammate.models import Team, TeamMember

DEMO_NICK = "测试用户一"  # 幂等标记：user01 昵称为该值时视为已灌入


def make_users() -> list[User]:
    users: list[User] = []
    for i in range(1, 11):
        u = User(
            username=f"user{i:02d}",
            email=f"user{i:02d}@whu.edu.cn",
            nickname=f"测试用户{'一二三四五六七八九十'[i-1]}",
            status=UserStatus.NORMAL.value,
            is_admin=False,
        )
        u.set_password("123456")
        users.append(u)
    return users


async def main() -> None:
    async with SessionLocal() as db:
        # ---------- 用户（已存在则复用并重置密码，保证 10 个都能用 123456 登录） ----------
        existing = (await db.scalars(select(User))).all()
        by_name = {u.username: u for u in existing}
        users: dict[str, User] = {}
        if "user01" in by_name and by_name["user01"].nickname == DEMO_NICK:
            print("[skip] 演示数据已灌入过（user01 昵称为 '测试用户一'），退出。")
            return
        for i in range(1, 11):
            name = f"user{i:02d}"
            if name in by_name:
                u = by_name[name]
                u.set_password("123456")
                u.nickname = f"测试用户{'一二三四五六七八九十'[i-1]}"
                u.status = UserStatus.NORMAL.value
            else:
                u = User(
                    username=name,
                    email=f"{name}@whu.edu.cn",
                    nickname=f"测试用户{'一二三四五六七八九十'[i-1]}",
                    status=UserStatus.NORMAL.value,
                )
                u.set_password("123456")
                db.add(u)
            users[name] = u
        await db.flush()
        print(f"[users] 10 个演示用户就绪（密码 123456）：{', '.join(users)}")

        # ---------- 二手交易：发布物品 + 交易会话 ----------
        item_specs = [
            ("user01", "九成新 AirPods 耳机", "自用半年，续航正常，无划痕", 39900, "电子产品", ItemStatus.ON_SALE),
            ("user01", "高数（上）教材+习题册", "张宇高数上下全套，附笔记", 2500, "书籍资料", ItemStatus.SOLD),
            ("user02", "捷安特山地自行车", "毕业出，链条刚保养过", 80000, "交通工具", ItemStatus.ON_SALE),
            ("user02", "宿舍护眼台灯", "三档调光，几乎全新", 4500, "日用百货", ItemStatus.RESERVED),
            ("user03", "考研数学真题解析", "2009-2024 全套，满页笔记", 3000, "书籍资料", ItemStatus.ON_SALE),
            ("user03", "斯伯丁篮球 7 号", "室内外通用，8 成新", 6000, "运动户外", ItemStatus.OFF_SHELF),
            ("user04", "秋冬针织连衣裙", "全新未拆吊牌，M 码", 8900, "美妆服饰", ItemStatus.ON_SALE),
        ]
        items: dict[str, Item] = {}
        for owner, title, desc, price, cat, status in item_specs:
            it = Item(
                owner_id=users[owner].id,
                title=title,
                description=desc,
                price=price,
                category=cat,
                status=status.value,
            )
            db.add(it)
            items[title] = it
        await db.flush()

        # 交易会话（买家发起，与消息会话关联）
        trade_specs = [
            (items["高数（上）教材+习题册"], "user05", "user01", TradeStatus.COMPLETED),
            (items["宿舍护眼台灯"], "user06", "user02", TradeStatus.IN_PROGRESS),
            (items["九成新 AirPods 耳机"], "user05", "user01", TradeStatus.PENDING),
        ]
        trades: dict[str, TradeSession] = {}
        for it, buyer, seller, status in trade_specs:
            ts = TradeSession(
                item_id=it.id, buyer_id=users[buyer].id, seller_id=users[seller].id, status=status.value
            )
            db.add(ts)
            trades[it.title] = ts
        await db.flush()
        print(f"[items] 发布 {len(items)} 件二手物品，建立 {len(trades)} 个交易会话")

        # ---------- 课程 + 课程评价 ----------
        course_specs = [
            ("CS201", "数据结构", "张伟", 3, "2026-2027-1", "计算机学院"),
            ("MATH101", "微积分（一）", "李建国", 5, "2026-2027-1", "数学与统计学院"),
            ("PHY101", "大学物理（上）", "王强", 4, "2026-2027-1", "物理科学与技术学院"),
            ("ECON101", "微观经济学", "陈静", 3, "2026-2027-1", "经济与管理学院"),
            ("ENG201", "大学英语（三）", "刘芳", 2, "2026-2027-1", "外国语言文学学院"),
            ("AI101", "人工智能导论", "周明", 2, "2026-2027-1", "通识教育中心"),
        ]
        courses: dict[str, Course] = {}
        for code, name, teacher, credits, sem, dept in course_specs:
            c = Course(code=code, name=name, teacher=teacher, credits=credits, semester=sem, department=dept)
            db.add(c)
            courses[name] = c
        await db.flush()

        review_specs = [
            ("user05", "数据结构", 5, "张老师板书清晰，作业量适中，期末有重点串讲，给分很友好。"),
            ("user05", "微积分（一）", 4, "内容扎实，习题量大，想拿高分需要刷题。"),
            ("user06", "数据结构", 4, "课程安排合理，实验稍多但收获很大。"),
            ("user06", "大学物理（上）", 5, "王老师讲得生动，实验课有趣，强烈推荐。"),
            ("user07", "微观经济学", 5, "案例丰富，理论与实际结合得很好。"),
            ("user07", "大学英语（三）", 3, "课堂互动多，但考核偏口语，内向的同学要提前准备。"),
        ]
        for uid, cname, rating, content in review_specs:
            db.add(CourseReview(course_id=courses[cname].id, user_id=users[uid].id, rating=rating, content=content))
        await db.flush()
        print(f"[course] 创建 {len(courses)} 门课程，{len(review_specs)} 条课程评价")

        # ---------- 食堂：档口/菜品 + 菜品评价 ----------
        canteens = {c.name: c for c in (await db.scalars(select(Canteen))).all()}
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
            ("user08", "黄焖鸡米饭", 4, "鸡肉入味，汤汁拌饭绝了，就是量有点少。"),
            ("user09", "麻辣烫（份）", 4, "食材新鲜，汤底可选，微辣刚好。"),
            ("user09", "红烧牛肉粉", 5, "牛肉给得多，汤头浓郁，回购多次。"),
            ("user10", "铁板鸡排饭", 4, "分量足，洋葱打底很香。"),
            ("user10", "三鲜豆皮", 5, "外皮酥脆内馅饱满，武汉老味道。"),
        ]
        for uid, dname, rating, content in dish_reviews:
            db.add(CanteenReview(dish_id=dishes[dname].id, user_id=users[uid].id, rating=rating, content=content))
        await db.flush()
        print(f"[canteen] 新增 {sum(len(s[2]) for s in stall_specs)} 道菜品（{len(stall_specs)} 个档口），{len(dish_reviews)} 条菜品评价")

        # ---------- 兼职：发布 + 申请 ----------
        job_specs = [
            ("user02", "图书馆自习区管理员助理", "整理书架、维护自习秩序，每周 3 个班次", "校图书馆", 15000, "助教/助管", JobStatus.OPEN),
            ("user02", "初二数学家教", "每周六下午 2 小时，上门辅导", "家教中心", 20000, "家教辅导", JobStatus.OPEN),
            ("user03", "校园咖啡品牌代理", "负责校内推广与团购配送", "某咖啡品牌", 12000, "校园代理", JobStatus.CLOSED),
        ]
        jobs: dict[str, Job] = {}
        for poster, title, desc, comp, salary, cat, status in job_specs:
            j = Job(
                poster_id=users[poster].id, title=title, description=desc,
                company=comp, salary=salary, category=cat, status=status.value,
            )
            db.add(j)
            jobs[title] = j
        await db.flush()

        app_specs = [
            ("user04", "图书馆自习区管理员助理", ApplicationStatus.ACCEPTED, "可以安排每周一二四晚班"),
            ("user05", "初二数学家教", ApplicationStatus.PENDING, "有两年家教经验，附简历"),
            ("user06", "校园咖啡品牌代理", ApplicationStatus.REJECTED, "对校内渠道熟悉"),
        ]
        for uid, jtitle, status, note in app_specs:
            db.add(JobApplication(job_id=jobs[jtitle].id, applicant_id=users[uid].id, status=status.value, note=note))
        await db.flush()
        print(f"[job] 发布 {len(jobs)} 个岗位，{len(app_specs)} 条申请")

        # ---------- 资源共享 ----------
        share_specs = [
            ("user06", "高数（上）期末真题+答案", "近五年真题整理，附手写解析", "期末复习题", 32),
            ("user06", "考研英语真题词汇笔记", "历年真题高频词汇整理，配合例句", "考研考证", 18),
            ("user07", "课程设计报告模板", "含目录/图表/参考文献格式，可直接套用", "实验报告模版", 45),
            ("user07", "Python 爬虫开源代码", "校园公开数据爬取示例，含反爬说明", "开源代码", 27),
        ]
        for owner, title, desc, cat, dls in share_specs:
            db.add(ShareResource(owner_id=users[owner].id, title=title, description=desc, category=cat, downloads=dls))
        await db.flush()
        print(f"[share] 上传 {len(share_specs)} 份共享资料")

        # ---------- 队友招募 ----------
        team_specs = [
            ("user08", "数学建模国赛 3 缺 1", "C 题方向，缺一名建模手/论文手", "建模手/论文手", TeamStatus.RECRUITING, "学术竞赛", 4, "微信：user08_model"),
            ("user09", "东湖夜跑搭子", "每周二四六晚 8 点，配速 6 分半", "无", TeamStatus.RECRUITING, "运动健身", 5, "QQ：run_with_me"),
            ("user10", "考研自习搭子", "图书馆 4 楼固定座位，互相监督打卡", "研友", TeamStatus.FULL, "考研考公", 3, "私信联系"),
        ]
        teams: dict[str, Team] = {}
        for creator, title, desc, roles, status, cat, mx, contact in team_specs:
            t = Team(
                creator_id=users[creator].id, title=title, description=desc,
                required_roles=roles, status=status.value, category=cat,
                max_members=mx, contact_info=contact,
            )
            db.add(t)
            teams[title] = t
        await db.flush()

        member_specs = [
            ("user01", "数学建模国赛 3 缺 1", "建模手", MemberStatus.ACTIVE),
            ("user02", "数学建模国赛 3 缺 1", "论文手", MemberStatus.PENDING),
            ("user03", "东湖夜跑搭子", "跑友", MemberStatus.ACTIVE),
            ("user04", "考研自习搭子", "研友", MemberStatus.ACTIVE),
        ]
        for uid, ttitle, role, status in member_specs:
            db.add(TeamMember(team_id=teams[ttitle].id, user_id=users[uid].id, role=role, status=status.value))
        await db.flush()
        print(f"[team] 发起 {len(teams)} 个招募，{len(member_specs)} 条入队记录")

        # ---------- 即时消息（direct + trade 会话） ----------
        conv_specs = [
            ("trade", trades["高数（上）教材+习题册"].id, ["user05", "user01"],
             [("user05", 0, "同学你好，高数教材还在吗？", True),
              ("user01", 0, "在的，九成新，附全套笔记", True),
              ("user05", 0, "我诚心要，校内哪里面交？", True),
              ("user01", 0, "东湖校区图书馆门口，随时", True),
              ("user05", 0, "好，那就约今天下午", True)]),
            ("trade", trades["宿舍护眼台灯"].id, ["user06", "user02"],
             [("user06", 0, "台灯还能便宜点吗？", True),
              ("user02", 0, "最低 40 了，基本全新", True),
              ("user06", 0, "行，周末当面验货", False)]),
            ("direct", None, ["user08", "user09"],
             [("user08", 0, "周六晚上东湖夜跑约吗？", True),
              ("user09", 0, "约！老时间老地方", True),
              ("user08", 0, "好嘞，我再拉一个人", False)]),
            ("direct", None, ["user01", "user05"],
             [("user05", 0, "耳机 350 能不能出？", True),
              ("user01", 0, "可以小刀，380 最低", False)]),
        ]
        msg_count = 0
        for conv_type, related_id, part_names, msgs in conv_specs:
            conv = Conversation(conv_type=conv_type, related_id=related_id)
            db.add(conv)
            await db.flush()
            for pn in part_names:
                db.add(Participant(conversation_id=str(conv.id), user_id=users[pn].id))
            for sender, mtype, content, is_read in msgs:
                db.add(Message(
                    conversation_id=str(conv.id), sender_id=users[sender].id,
                    type=mtype, content=content, is_read=is_read,
                ))
                msg_count += 1
        await db.flush()
        print(f"[message] 新增 {len(conv_specs)} 个会话、{msg_count} 条消息")

        # ---------- 举报工单 ----------
        report_specs = [
            ("user03", ReportTargetType.ITEM, items["九成新 AirPods 耳机"].id,
             "怀疑为高仿耳机，卖家描述与实物不符", ReportStatus.PENDING, None, None),
            ("user04", ReportTargetType.USER, users["user03"].id,
             "该用户发布的兼职信息疑似虚假引流", ReportStatus.PENDING, None, None),
            ("user05", ReportTargetType.MESSAGE, str(conv_specs[0][0]),
             "会话中诱导线下交易，疑似诈骗", ReportStatus.RESOLVED, "resolve", "已核实并处理，账号已警告"),
            ("user06", ReportTargetType.SHARE, None,
             "上传内容疑似抄袭他人课程设计", ReportStatus.REJECTED, "reject", "证据不足，驳回举报"),
            ("user07", ReportTargetType.COMMENT, None,
             "评论内容恶意攻击授课教师", ReportStatus.PENDING, None, None),
        ]
        # 修正 message/share/comment 的 target_id：使用真实记录 id
        msg_target = (await db.scalars(select(Message))).all()[-1]
        share_target = (await db.scalars(select(ShareResource))).all()[0]
        review_target = (await db.scalars(select(CourseReview))).all()[0]
        report_specs[2] = (report_specs[2][0], ReportTargetType.MESSAGE, msg_target.id, report_specs[2][3], report_specs[2][4], report_specs[2][5], report_specs[2][6])
        report_specs[3] = (report_specs[3][0], ReportTargetType.SHARE, share_target.id, report_specs[3][3], report_specs[3][4], report_specs[3][5], report_specs[3][6])
        report_specs[4] = (report_specs[4][0], ReportTargetType.COMMENT, review_target.id, report_specs[4][3], report_specs[4][4], report_specs[4][5], report_specs[4][6])
        for reporter, ttype, tid, reason, status, action, note in report_specs:
            rp = Report(
                reporter_id=users[reporter].id, target_type=ttype.value,
                target_id=tid, reason=reason, status=status.value,
            )
            db.add(rp)
            await db.flush()
            if action:
                db.add(ReportLog(report_id=str(rp.id), action=action, note=note))
        await db.flush()
        print(f"[report] 新增 {len(report_specs)} 条举报工单（含处理日志）")

        await db.commit()
        print("\n=== 灌入完成：10 用户（123456）已覆盖 二手/课程/食堂/兼职/分享/组队/消息/举报 全功能 ===")


if __name__ == "__main__":
    asyncio.run(main())
