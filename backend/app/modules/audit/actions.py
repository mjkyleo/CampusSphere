"""审计动作常量。

集中定义而非散落各处写字符串字面量，原因：
1. 后台按 action 下拉筛选时，需要一个权威取值清单；
2. 避免 "login" / "user_login" 这类拼写漂移导致查不全。
"""


class AuditAction:
    """动作标识。命名规则：``对象.动作``，全小写。"""

    # ---- 认证 ----
    LOGIN = "auth.login"
    LOGIN_FAILED = "auth.login_failed"
    LOGOUT = "auth.logout"
    REGISTER = "auth.register"
    REGISTER_FAILED = "auth.register_failed"
    EMAIL_REGISTER = "auth.email_register"
    PHONE_LOGIN = "auth.phone_login"
    SEND_CODE = "auth.send_code"
    SEND_CODE_FAILED = "auth.send_code_failed"
    REFRESH_TOKEN = "auth.refresh_token"
    BIND_EMAIL = "auth.bind_email"
    BIND_PHONE = "auth.bind_phone"

    # ---- 管理员 ----
    ADMIN_LOGIN = "admin.login"
    ADMIN_LOGIN_FAILED = "admin.login_failed"
    ADMIN_BAN_USER = "admin.ban_user"
    ADMIN_UNBAN_USER = "admin.unban_user"
    ADMIN_PROMOTE_USER = "admin.promote_user"
    ADMIN_AUDIT_ITEM = "admin.audit_item"
    ADMIN_DELETE_ITEM = "admin.delete_item"
    ADMIN_UPDATE_CONFIG = "admin.update_config"

    # ---- 内容 ----
    ITEM_CREATE = "item.create"
    ITEM_UPDATE = "item.update"
    ITEM_DELETE = "item.delete"


class AuditResult:
    """结果标识。"""

    SUCCESS = "success"
    FAILURE = "failure"


class ActorType:
    """操作主体类型。"""

    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"
    ANONYMOUS = "anonymous"


ACTION_LABELS: dict[str, str] = {
    AuditAction.LOGIN: "用户登录",
    AuditAction.LOGIN_FAILED: "登录失败",
    AuditAction.LOGOUT: "用户登出",
    AuditAction.REGISTER: "用户注册",
    AuditAction.REGISTER_FAILED: "注册失败",
    AuditAction.EMAIL_REGISTER: "邮箱注册",
    AuditAction.PHONE_LOGIN: "手机号登录",
    AuditAction.SEND_CODE: "发送验证码",
    AuditAction.SEND_CODE_FAILED: "发送验证码失败",
    AuditAction.REFRESH_TOKEN: "刷新令牌",
    AuditAction.BIND_EMAIL: "绑定邮箱",
    AuditAction.BIND_PHONE: "绑定手机号",
    AuditAction.ADMIN_LOGIN: "管理员登录",
    AuditAction.ADMIN_LOGIN_FAILED: "管理员登录失败",
    AuditAction.ADMIN_BAN_USER: "封禁用户",
    AuditAction.ADMIN_UNBAN_USER: "解封用户",
    AuditAction.ADMIN_PROMOTE_USER: "提升管理员",
    AuditAction.ADMIN_AUDIT_ITEM: "审核物品",
    AuditAction.ADMIN_DELETE_ITEM: "删除物品",
    AuditAction.ADMIN_UPDATE_CONFIG: "修改配置",
    AuditAction.ITEM_CREATE: "发布物品",
    AuditAction.ITEM_UPDATE: "编辑物品",
    AuditAction.ITEM_DELETE: "删除物品",
}

RESULT_LABELS: dict[str, str] = {
    AuditResult.SUCCESS: "成功",
    AuditResult.FAILURE: "失败",
}

ACTOR_LABELS: dict[str, str] = {
    ActorType.USER: "用户",
    ActorType.ADMIN: "管理员",
    ActorType.SYSTEM: "系统",
    ActorType.ANONYMOUS: "匿名",
}
