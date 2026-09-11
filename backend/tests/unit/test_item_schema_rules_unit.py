"""Task 2 单元测试：Pydantic 业务规则引擎（金额契约 + 跨字段校验）。

覆盖点：
1. 金额契约：Service 层拿到的永远是「纯整数分」。
2. 拦住 Pydantic lax 模式会**静默吞掉**的脏数据（bool / 小数 / 字符串）。
3. 跨字段规则：电子产品图片数、零元挂售。
4. 规则阈值可通过配置开关（不重新发版即可调整严格程度）。

注意前提：**后端不做元→分转换**。前端 ``toCents()`` 已完成转换，
后端再乘一次 100 会造成双重转换事故（12.50 元 → 125000 分）。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.modules.item.schemas import (
    MAX_PRICE_CENTS,
    ItemCreate,
    ItemUpdate,
)


def _create(**overrides):
    base = {"title": "闲置自行车", "price": 12000}
    base.update(overrides)
    return ItemCreate(**base)


# ---------------------------------------------------------------------------
# 金额契约：纯整数分
# ---------------------------------------------------------------------------
def test_integer_cents_pass_through_unchanged() -> None:
    """契约核心：19900 进，19900 出 —— 后端不做任何单位换算。"""
    assert _create(price=19900).price == 19900


def test_boolean_price_is_rejected() -> None:
    """最危险的一类：bool 是 int 子类，lax 模式下 True 会静默变成 1 分。"""
    with pytest.raises(ValidationError) as exc:
        _create(price=True)
    assert "布尔值" in str(exc.value)


def test_float_price_is_rejected() -> None:
    """12.0 本会被静默转成 12，掩盖"前端传错单位"的问题。"""
    with pytest.raises(ValidationError) as exc:
        _create(price=12.0)
    assert "小数" in str(exc.value)


def test_string_price_is_rejected() -> None:
    """"12" 本会被静默转成 12，掩盖前端未做数值转换的问题。"""
    with pytest.raises(ValidationError) as exc:
        _create(price="12")
    assert "字符串" in str(exc.value)


def test_negative_price_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _create(price=-1)


def test_price_above_ceiling_is_rejected() -> None:
    """防御手误多敲 0 或被篡改的请求体污染市集排序。"""
    with pytest.raises(ValidationError) as exc:
        _create(price=MAX_PRICE_CENTS + 1)
    assert "上限" in str(exc.value)


def test_price_at_ceiling_is_accepted() -> None:
    assert _create(price=MAX_PRICE_CENTS).price == MAX_PRICE_CENTS


# ---------------------------------------------------------------------------
# 跨字段规则：零元挂售（默认开启）
# ---------------------------------------------------------------------------
def test_zero_price_publish_is_rejected() -> None:
    """禁止零元发布：price 默认为 0，漏传价格不再静默产生 0 元商品。"""
    with pytest.raises(ValidationError) as exc:
        _create(price=0)
    assert "零元" in str(exc.value)


def test_zero_price_rule_can_be_disabled_by_config(monkeypatch) -> None:
    """阈值外置：运营关闭该规则后无需改代码即可放行。"""
    monkeypatch.setattr(
        "app.modules.item.schemas.settings",
        type("S", (), {"items": {"rules": {"forbid_zero_price_on_sale": False}}})(),
    )
    assert _create(price=0).price == 0


def test_update_to_on_sale_with_zero_price_is_rejected() -> None:
    """部分更新：显式把价格改成 0 且目标为在售 → 拒绝。"""
    with pytest.raises(ValidationError) as exc:
        ItemUpdate(price=0, status=0)
    assert "零元" in str(exc.value)


def test_update_to_off_shelf_with_zero_price_is_allowed() -> None:
    """下架（非挂售）态允许零元 —— 规则只针对"在售"。"""
    from app.common.enums import ItemStatus

    assert ItemUpdate(price=0, status=ItemStatus.OFF_SHELF.value).price == 0


def test_update_without_price_does_not_trigger_rule() -> None:
    """只改状态、不改价格：Schema 无从得知库中现价，不应误报。"""
    from app.common.enums import ItemStatus

    assert ItemUpdate(status=ItemStatus.ON_SALE.value).price is None


# ---------------------------------------------------------------------------
# 跨字段规则：电子产品图片数（默认关闭，可开启）
# ---------------------------------------------------------------------------
def _images(n: int) -> list[dict]:
    return [{"object_key": f"misc/{i}.bin", "sort_order": i} for i in range(n)]


def test_electronics_rule_is_off_by_default() -> None:
    """默认不启用：避免前端未配合时把真实用户挡在发布流程外。"""
    assert _create(category="电子产品", images=_images(1)).category == "电子产品"


def test_electronics_rule_enforced_when_enabled(monkeypatch) -> None:
    """配置开启后，电子产品少于 3 张图即被拒。"""
    monkeypatch.setattr(
        "app.modules.item.schemas.settings",
        type("S", (), {"items": {"rules": {"electronics_min_images": 3}}})(),
    )
    with pytest.raises(ValidationError) as exc:
        _create(category="电子产品", images=_images(2))
    assert "电子产品" in str(exc.value)

    # 达到阈值即放行
    assert len(_create(category="电子产品", images=_images(3)).images) == 3


def test_image_rule_does_not_apply_to_other_categories(monkeypatch) -> None:
    """规则只对电子产品生效，其他分类不受影响。"""
    monkeypatch.setattr(
        "app.modules.item.schemas.settings",
        type("S", (), {"items": {"rules": {"electronics_min_images": 3}}})(),
    )
    assert _create(category="书籍资料", images=_images(1)).category == "书籍资料"
