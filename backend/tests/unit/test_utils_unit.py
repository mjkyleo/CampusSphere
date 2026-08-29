"""通用工具函数单元测试：校验、脱敏、分页、类型转换。

这些函数被所有模块复用（列表分页、隐私脱敏、验证码生成），
属于"改一处影响全局"的基础设施，因此做参数化穷举覆盖。
"""

from __future__ import annotations

import pytest

from app.common.utils import (
    Page,
    PageResult,
    generate_code,
    is_valid_email,
    is_valid_phone,
    mask_email,
    mask_phone,
    safe_int,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# 手机号校验
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("13812345678", True),
        ("19900001111", True),
        ("12345678901", False),  # 第二位必须是 3-9
        ("1381234567", False),  # 10 位
        ("138123456789", False),  # 12 位
        ("", False),
        ("+8613812345678", False),  # 不带国际区号
        (None, False),
    ],
)
def test_is_valid_phone(value, expected):
    """中国大陆手机号：1 开头、第二位 3-9、共 11 位。"""
    assert is_valid_phone(value) is expected


# ---------------------------------------------------------------------------
# 邮箱校验
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("student@campus.edu.cn", True),
        ("a.b+c@example.com", True),
        ("no-at-sign", False),
        ("a@b", False),  # 缺顶级域
        ("a@@b.com", False),
        ("", False),
        (None, False),
    ],
)
def test_is_valid_email(value, expected):
    """邮箱格式校验（仅格式，域名白名单由注册服务另行校验）。"""
    assert is_valid_email(value) is expected


# ---------------------------------------------------------------------------
# 脱敏（隐私保护）
# ---------------------------------------------------------------------------
def test_mask_phone_standard_11_digits():
    """11 位手机号：保留前 3 后 4。"""
    assert mask_phone("13812345678") == "138****5678"


def test_mask_phone_non_standard_length():
    """非 11 位：保留前 3 后 2，避免长号码泄露过多。"""
    assert mask_phone("12345") == "123***45"


@pytest.mark.parametrize("value", [None, ""])
def test_mask_phone_falsy_returns_original(value):
    """空值原样返回（调用方无需额外判空）。"""
    assert mask_phone(value) == value


def test_mask_email_hides_local_part():
    """邮箱：只保留首位，其余打星，域名完整（便于用户辨认）。"""
    assert mask_email("alice@campus.edu.cn") == "a****@campus.edu.cn"


def test_mask_email_single_char_local():
    """单字符用户名：整个本地部分替换为星号。"""
    assert mask_email("a@example.com") == "*@example.com"


def test_mask_email_without_at_returns_original():
    """非法邮箱原样返回，不做部分脱敏（避免产生误导性输出）。"""
    assert mask_email("not-an-email") == "not-an-email"


# ---------------------------------------------------------------------------
# 分页
# ---------------------------------------------------------------------------
def test_page_offset_and_limit():
    """分页偏移量计算。"""
    assert (Page(page=1, page_size=20).offset, Page(page=1, page_size=20).limit) == (0, 20)
    assert Page(page=3, page_size=10).offset == 20


def test_page_clamps_invalid_page_number():
    """页码小于 1 时回退到第 1 页（避免负 offset 导致 SQL 异常）。"""
    assert Page(page=0, page_size=10).offset == 0
    assert Page(page=-5, page_size=10).offset == 0


def test_page_result_pages_calculation():
    """总页数向上取整。"""
    assert PageResult(items=[], total=0, page=1, page_size=20).pages == 0
    assert PageResult(items=[], total=1, page=1, page_size=20).pages == 1
    assert PageResult(items=[], total=21, page=1, page_size=20).pages == 2


def test_page_result_zero_page_size_is_safe():
    """page_size 为 0 时 pages 返回 0，不触发除零异常。"""
    assert PageResult(items=[], total=10, page=1, page_size=0).pages == 0


def test_page_result_to_dict_with_mapper():
    """to_dict 支持自定义序列化（避免各视图重复写分页响应拼装）。"""
    result = PageResult(items=[1, 2, 3], total=3, page=1, page_size=20)
    data = result.to_dict(lambda x: {"v": x})
    assert data["items"] == [{"v": 1}, {"v": 2}, {"v": 3}]
    assert data["total"] == 3 and data["pages"] == 1


# ---------------------------------------------------------------------------
# 类型转换
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("value", "default", "expected"),
    [
        ("42", 0, 42),
        (3.9, 0, 3),  # 浮点截断
        ("abc", 7, 7),  # 非法值回落默认值
        (None, 5, 5),
        (True, 0, 1),  # 布尔转 int
    ],
)
def test_safe_int(value, default, expected):
    """安全转 int：非法输入回落到默认值而非抛异常。"""
    assert safe_int(value, default) == expected


def test_generate_code_default_six_digits():
    """验证码默认 6 位数字。"""
    code = generate_code()
    assert len(code) == 6 and code.isdigit()
