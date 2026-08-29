"""测试数据工厂（factory_boy）。

设计要点
--------
1. **为什么不用 ``SQLAlchemyModelFactory``**
   项目数据层是 **异步** SQLAlchemy（``AsyncSession``），而 factory_boy 的
   ``SQLAlchemyModelFactory`` 依赖同步 session 做 ``session.add/commit``，
   在异步会话上直接调用会在 flush 时抛错。因此这里统一采用
   **「先 build 内存实例 → 再由测试显式异步持久化」** 的模式::

       user = await create_async(session, UserFactory, username="alice")

   这样既保留 factory_boy 的声明式字段、序列（Sequence）与后处理钩子能力，
   又完全兼容 ``AsyncSession``。

2. **build vs create**
   - ``XxxFactory.build()``：只构造内存实例，**不落库**，适合纯单元测试（极快）；
   - ``await create_async(session, XxxFactory, **overrides)``：落库并 flush，
     适合集成测试。主键由 ``PKMixin`` 自动生成 UUID，工厂不干预。

3. **事务隔离**
   持久化助手只做 ``flush`` 不做 ``commit``，配合``tests/conftest.py`` 中
   function 级 ``test_engine``（每次重建表结构）实现用例间数据隔离；
   需要跨请求可见时用 ``await session.commit()`` 显式提交。

4. **密码**
   ``UserFactory`` 通过后处理钩子调用 ``User.set_password()`` 生成 bcrypt 哈希，
   默认明文为 ``DEFAULT_PASSWORD``；可用 ``with_password="xxx"`` 覆盖。
"""

from __future__ import annotations

import uuid
from typing import Any, TypeVar

import factory

from app.common.enums import ItemStatus, ReportStatus, UserStatus
from app.modules.auth.models import User
from app.modules.canteen.models import Canteen, CanteenReview, Dish, Stall
from app.modules.course.models import Course, CourseReview
from app.modules.item.models import Item, ItemImage
from app.modules.report.models import Report

DEFAULT_PASSWORD = "Test@12345"

F = TypeVar("F", bound=factory.Factory)


def unique_hex(length: int = 8) -> str:
    """生成短随机串，用于构造唯一用户名 / 编号等。"""
    return uuid.uuid4().hex[:length]


# ---------------------------------------------------------------------------
# 异步持久化助手
# ---------------------------------------------------------------------------
async def create_async(
    session, factory_class: type[F], commit: bool = False, **kwargs: Any
):
    """构造一个工厂实例并写入异步会话。

    Args:
        session: ``AsyncSession``。
        factory_class: factory_boy 工厂类。
        commit: 是否提交事务。**HTTP 请求走的是另一个会话**，若用例里
            先播种数据再调 API，必须 ``commit=True`` 否则接口看不到。
        **kwargs: 覆盖工厂默认字段。

    Returns:
        已持久化的模型实例（已 refresh，可读取服务端默认值）。
    """
    obj = factory_class.build(**kwargs)
    session.add(obj)
    await session.flush()
    await session.refresh(obj)
    if commit:
        await session.commit()
    return obj


async def create_batch_async(
    session, factory_class: type[F], size: int, commit: bool = False, **kwargs: Any
):
    """批量构造并持久化，返回实例列表。"""
    return [
        await create_async(session, factory_class, commit=commit, **kwargs)
        for _ in range(size)
    ]


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------
class UserFactory(factory.Factory):
    """平台用户。默认密码 ``DEFAULT_PASSWORD``。"""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}_{unique_hex(4)}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@campus.edu.cn")
    phone = None
    nickname = factory.LazyAttribute(lambda o: f"昵称_{o.username}")
    avatar = None
    status = UserStatus.NORMAL.value
    is_admin = False

    @factory.post_generation
    def with_password(obj, create, extracted, **kwargs):
        """``UserFactory.build(with_password="abc")`` → 用指定明文生成哈希。

        不传时使用 ``DEFAULT_PASSWORD``，保证登录类测试可复用同一常量。
        """
        obj.set_password(extracted or DEFAULT_PASSWORD)


class AdminFactory(UserFactory):
    """管理员用户（``is_admin=True``），用户名带 admin 前缀。"""

    username = factory.Sequence(lambda n: f"admin_{n}_{unique_hex(4)}")
    is_admin = True


# ---------------------------------------------------------------------------
# 二手物品
# ---------------------------------------------------------------------------
class ItemFactory(factory.Factory):
    """二手物品。``owner_id`` 需显式传入真实用户 id（外键）。"""

    class Meta:
        model = Item

    owner_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    title = factory.Sequence(lambda n: f"二手物品_{n}_{unique_hex(4)}")
    description = factory.LazyAttribute(lambda o: f"{o.title} 的描述")
    price = 1500  # 单位：分
    category = "book"
    status = ItemStatus.ON_SALE.value


class ItemImageFactory(factory.Factory):
    """物品图片（只存对象存储 key，不落真实文件）。"""

    class Meta:
        model = ItemImage

    item_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    object_key = factory.LazyFunction(lambda: f"items/{uuid.uuid4().hex}.bin")
    sort_order = 0


# ---------------------------------------------------------------------------
# 课程与评价
# ---------------------------------------------------------------------------
class CourseFactory(factory.Factory):
    """课程。"""

    class Meta:
        model = Course

    code = factory.Sequence(lambda n: f"CS{1000 + n}_{unique_hex(3)}")
    name = factory.Sequence(lambda n: f"课程_{n}")
    teacher = factory.Sequence(lambda n: f"教师_{n}")
    credits = 3
    semester = "2026-2027-1"
    department = "计算机学院"


class CourseReviewFactory(factory.Factory):
    """课程评价（1-5 星）。"""

    class Meta:
        model = CourseReview

    course_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    rating = 5
    content = factory.Sequence(lambda n: f"课程评价内容_{n}")


# ---------------------------------------------------------------------------
# 食堂 / 档口 / 菜品与评价
# ---------------------------------------------------------------------------
class CanteenFactory(factory.Factory):
    """食堂。"""

    class Meta:
        model = Canteen

    name = factory.Sequence(lambda n: f"食堂_{n}_{unique_hex(3)}")
    location = "校园东区"
    image = ""


class StallFactory(factory.Factory):
    """档口。``canteen_id`` 需显式传入。"""

    class Meta:
        model = Stall

    canteen_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.Sequence(lambda n: f"档口_{n}")
    image = ""


class DishFactory(factory.Factory):
    """菜品。``stall_id`` 需显式传入。"""

    class Meta:
        model = Dish

    stall_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    name = factory.Sequence(lambda n: f"菜品_{n}")
    price = 1200  # 单位：分
    image = ""


class CanteenReviewFactory(factory.Factory):
    """菜品评价。``dish_id`` / ``user_id`` 需显式传入。"""

    class Meta:
        model = CanteenReview

    dish_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    user_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    rating = 5
    content = factory.Sequence(lambda n: f"菜品评价内容_{n}")


# ---------------------------------------------------------------------------
# 举报工单
# ---------------------------------------------------------------------------
class ReportFactory(factory.Factory):
    """举报工单，默认待处理（PENDING）。"""

    class Meta:
        model = Report

    reporter_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    target_type = "item"
    target_id = factory.LazyFunction(lambda: str(uuid.uuid4()))
    reason = factory.Sequence(lambda n: f"举报原因_{n}")
    status = ReportStatus.PENDING.value
    handled_by = None
