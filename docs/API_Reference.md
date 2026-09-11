# campus-life-platform — API 接口文档

> 版本：`1.0.0` | 接口总数：128 | 生成时间：2026-09-05 17:55

> 约定：业务错误统一返回 **HTTP 200**，错误码在响应体 `code` 字段（如 40100 未认证 / 40300 禁止 / 40400 未找到 / 40900 冲突 / 42200 参数错误）。

## 目录

- [admin](#admin)
- [ai](#ai)
- [audit](#audit)
- [auth](#auth)
- [canteen](#canteen)
- [course](#course)
- [files](#files)
- [item](#item)
- [job](#job)
- [launcher](#launcher)
- [message](#message)
- [report](#report)
- [share](#share)
- [teammate](#teammate)
- [user](#user)
- [默认](#默认)

## 通用数据模型

### `AdminDiscoverRequest`

用网关密钥换取短时网关令牌。

- `gateway_key`：string，必填。

### `AdminLoginRequest`

- `username`：string，必填。
- `password`：string，必填。

### `AdminOut`

- `id`：string(uuid)，必填。
- `username`：string，必填。
- `role_id`：string | null，可选。
- `disabled`：boolean，可选。
- `permissions`：array[string]，可选。

### `AdminPromoteRequest`

将普通用户提升为管理员时设置其后台登录密码（必填）。

- `password`：string，必填。

### `AdminTokenResponse`

- `access_token`：string，必填。
- `refresh_token`：string，必填。
- `token_type`：string，可选。

### `AiFeatureConfig`

AI 智能助手功能开关（DB 值覆盖 school.yaml 默认值）。

个人开发者无大模型 API 额度时保持关闭，前端隐藏所有 AI 入口；
额度到位后管理员在后台一键开启即可上线。

- `enabled`：boolean，可选。
- `model`：string，可选。

### `AiStatusOut`

AI 功能状态（公开端点，供前端决定是否渲染 AI 区块）。

- `enabled`：boolean，可选。
- `available`：boolean，可选。
- `message`：string，可选。

### `ApiResponse_AdminOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AdminOut | null，可选。

### `ApiResponse_AdminTokenResponse_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AdminTokenResponse | null，可选。

### `ApiResponse_AiFeatureConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AiFeatureConfig | null，可选。

### `ApiResponse_AiStatusOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AiStatusOut | null，可选。

### `ApiResponse_AuditLogPage_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AuditLogPage | null，可选。

### `ApiResponse_BindingsOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：BindingsOut | null，可选。

### `ApiResponse_CanteenConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CanteenConfig | null，可选。

### `ApiResponse_CanteenOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CanteenOut | null，可选。

### `ApiResponse_CanteenReviewOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CanteenReviewOut | null，可选。

### `ApiResponse_CategorizeOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CategorizeOut | null，可选。

### `ApiResponse_CourseDepartmentGroupsConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CourseDepartmentGroupsConfig | null，可选。

### `ApiResponse_CourseDepartmentsConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CourseDepartmentsConfig | null，可选。

### `ApiResponse_CourseOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CourseOut | null，可选。

### `ApiResponse_CourseReviewOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CourseReviewOut | null，可选。

### `ApiResponse_DishOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：DishOut | null，可选。

### `ApiResponse_EmailRegisterConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：EmailRegisterConfig | null，可选。

### `ApiResponse_EmailRegisterResponse_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：EmailRegisterResponse | null，可选。

### `ApiResponse_ItemCategoriesConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ItemCategoriesConfig | null，可选。

### `ApiResponse_ItemOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ItemOut | null，可选。

### `ApiResponse_ItemReviewConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ItemReviewConfig | null，可选。

### `ApiResponse_JobApplicationOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：JobApplicationOut | null，可选。

### `ApiResponse_JobCategoriesConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：JobCategoriesConfig | null，可选。

### `ApiResponse_JobOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：JobOut | null，可选。

### `ApiResponse_NoneType_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：null，可选。

### `ApiResponse_ReportOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ReportOut | null，可选。

### `ApiResponse_SendCodeOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：SendCodeOut | null，可选。

### `ApiResponse_ShareCategoriesConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ShareCategoriesConfig | null，可选。

### `ApiResponse_ShareOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ShareOut | null，可选。

### `ApiResponse_SliderCaptchaOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：SliderCaptchaOut | null，可选。

### `ApiResponse_SliderVerifyOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：SliderVerifyOut | null，可选。

### `ApiResponse_StallOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：StallOut | null，可选。

### `ApiResponse_TeamMemberOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：TeamMemberOut | null，可选。

### `ApiResponse_TeamOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：TeamOut | null，可选。

### `ApiResponse_TeammateCategoriesConfig_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：TeammateCategoriesConfig | null，可选。

### `ApiResponse_TokenResponse_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：TokenResponse | null，可选。

### `ApiResponse_TradeSessionOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：TradeSessionOut | null，可选。

### `ApiResponse_UserOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：UserOut | null，可选。

### `ApiResponse_UserProfileOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：UserProfileOut | null，可选。

### `ApiResponse_dict_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：object | null，可选。

### `ApiResponse_list_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：array[any] | null，可选。

### `ApiResponse_list_AuditActionOption__`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：array[AuditActionOption] | null，可选。

### `ApiResponse_str_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：string | null，可选。

### `AuditActionOption`

动作下拉选项。

- `value`：string，必填。
- `label`：string，必填。

### `AuditLogOut`

单条审计记录。

额外附带 ``action_label`` / ``result_label`` / ``actor_type_label``
三个中文字段，避免前端自己再维护一份动作字典（两处字典迟早会不同步）。

- `id`：string，必填。
- `created_at`：string(date-time)，必填。
- `actor_type`：string，必填。
- `actor_id`：string | null，可选。
- `actor_label`：string，可选。
- `action`：string，必填。
- `result`：string，可选。
- `target_type`：string，可选。
- `target_id`：string | null，可选。
- `detail`：object，可选。
- `ip`：string，可选。
- `user_agent`：string，可选。
- `request_id`：string，可选。
- `action_label`：string，可选。
- `result_label`：string，可选。
- `actor_type_label`：string，可选。

### `AuditLogPage`

分页结果。

- `items`：array[AuditLogOut]，可选。
  - `id`：string，必填。
  - `created_at`：string(date-time)，必填。
  - `actor_type`：string，必填。
  - `actor_id`：string | null，可选。
  - `actor_label`：string，可选。
  - `action`：string，必填。
  - `result`：string，可选。
  - `target_type`：string，可选。
  - `target_id`：string | null，可选。
  - `detail`：object，可选。
  - `ip`：string，可选。
  - `user_agent`：string，可选。
  - `request_id`：string，可选。
  - `action_label`：string，可选。
  - `result_label`：string，可选。
  - `actor_type_label`：string，可选。
- `total`：integer，可选。
- `limit`：integer，可选。
- `offset`：integer，可选。

### `BanRequest`

- `reason`：string，可选。

### `BindEmailRequest`

- `email`：string(email)，必填。
- `code`：string，必填。邮箱验证码（purpose=bind_email）

### `BindOAuthRequest`

- `provider`：string，必填。wechat/qq
- `code`：string，必填。
- `redirect_uri`：string，可选。
- `state`：string | null，可选。OAuth state（防 CSRF）

### `BindPhoneRequest`

- `phone`：string，必填。
- `code`：string，必填。短信验证码（purpose=bind_phone）

### `BindingsOut`

- `username`：string，必填。
- `email`：string | null，可选。
- `phone`：string | null，可选。
- `oauth`：array[string]，可选。

### `Body_presign_api_files_presign_post`

- `prefix`：string，可选。
- `filename`：string，可选。

### `Body_upload_api_files_upload_post`

- `key`：string，必填。
- `file`：string，必填。

### `CanteenConfig`

食堂维度枚举配置（后台可动态配置）。

``zones`` 为「学部 → 餐饮区列表」映射；``semesters`` 为空表示不启用
学期筛选，``current_semester`` 为空表示前端默认展示全部学期。

- `campuses`：array[string]，可选。
- `zones`：object，可选。
- `types`：array[string]，可选。
- `semesters`：array[string]，可选。
- `current_semester`：string，可选。

### `CanteenCreate`

- `name`：string，必填。
- `location`：string，可选。
- `image`：string，可选。
- `campus`：string，可选。
- `zone`：string，可选。
- `canteen_type`：string，可选。
- `floor`：string，可选。
- `description`：string，可选。
- `features`：array[string]，可选。
- `popular_dishes`：array[string]，可选。
- `opening_hours`：string，可选。
- `semester`：string，可选。

### `CanteenOut`

- `id`：string(uuid)，必填。
- `name`：string，必填。
- `location`：string，必填。
- `image`：string，必填。
- `campus`：string，可选。
- `zone`：string，可选。
- `canteen_type`：string，可选。
- `floor`：string，可选。
- `description`：string，可选。
- `features`：array[string]，可选。
- `popular_dishes`：array[string]，可选。
- `opening_hours`：string，可选。
- `semester`：string，可选。
- `stalls`：array[StallOut]，可选。
  - `id`：string(uuid)，必填。
  - `canteen_id`：string，必填。
  - `name`：string，必填。
  - `image`：string，必填。
  - `dishes`：array[DishOut]，可选。
    - `id`：string(uuid)，必填。
    - `stall_id`：string，必填。
    - `name`：string，必填。
    - `price`：integer，必填。
    - `image`：string，必填。

### `CanteenReviewCreate`

- `rating`：integer，可选。
- `content`：string，可选。

### `CanteenReviewOut`

- `id`：string(uuid)，必填。
- `dish_id`：string，必填。
- `user_id`：string，必填。
- `rating`：integer，必填。
- `content`：string，必填。

### `CategorizeOut`

内容分类结果。

- `category`：string，必填。
- `isSafe`：boolean，必填。
- `summary`：string，必填。

### `CategorizeRequest`

内容自动分类与安全预审（发帖场景预留）。

- `content`：string，必填。

### `CourseCreate`

- `code`：string，必填。
- `name`：string，必填。
- `teacher`：string，可选。
- `credits`：integer，可选。
- `semester`：string，可选。
- `department`：string，可选。

### `CourseDepartmentGroupsConfig`

课程院系按学部分组（后台可动态配置）。

用于前端「学部 Tab → 院系 chips」两级筛选，避免 40+ 院系平铺溢出。

- `groups`：array[DepartmentGroup]，可选。
  - `group`：string，必填。
  - `departments`：array[string]，可选。

### `CourseDepartmentsConfig`

课程开课院系列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

- `departments`：array[string]，可选。

### `CourseOut`

- `id`：string(uuid)，必填。
- `code`：string，必填。
- `name`：string，必填。
- `teacher`：string，必填。
- `credits`：integer，必填。
- `semester`：string，必填。
- `department`：string，必填。

### `CourseReviewCreate`

- `rating`：integer，可选。
- `content`：string，可选。

### `CourseReviewOut`

- `id`：string(uuid)，必填。
- `course_id`：string，必填。
- `user_id`：string，必填。
- `rating`：integer，必填。
- `content`：string，必填。

### `CourseSummaryRequest`

课程评价 AI 汇总提炼。

- `reviewTexts`：array[string]，必填。

### `DepartmentGroup`

一个学部及其下属院系。

- `group`：string，必填。
- `departments`：array[string]，可选。

### `DishCreate`

- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，可选。单位：分
- `image`：string，可选。

### `DishOut`

- `id`：string(uuid)，必填。
- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，必填。
- `image`：string，必填。

### `EmailRegisterConfig`

邮箱注册规则（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

- `enabled`：boolean，可选。
- `domains`：array[string]，可选。
- `pattern`：string，可选。

### `EmailRegisterRequest`

- `email`：string(email)，必填。
- `password`：string，必填。
- `nickname`：string | null，可选。
- `code`：string，必填。邮箱验证码（purpose=register）

### `EmailRegisterResponse`

邮箱注册响应：在令牌基础上附带新生成的账号信息，便于前端直接展示。

- `access_token`：string，必填。
- `refresh_token`：string，必填。
- `token_type`：string，可选。
- `expires_in`：integer，必填。
- `email`：string | null，可选。
- `username`：string，必填。

### `GeetestVerifyRequest`

极验前端验证通过后回传的四个字段，服务端据此做二次校验。

字段名由极验 SDK 定义（``captcha.getValidate()`` 的返回），不可自定义。

- `lot_number`：string，必填。验证流水号
- `captcha_output`：string，必填。验证输出信息
- `pass_token`：string，必填。验证通过标识
- `gen_time`：string，必填。验证通过时间戳

### `HTTPValidationError`

- `detail`：array[ValidationError]，可选。
  - `loc`：array[string | integer]，必填。
  - `msg`：string，必填。
  - `type`：string，必填。
  - `input`：any，可选。
  - `ctx`：object，可选。

### `InsightRequest`

首页校园智能灵感。

- `topic`：string，必填。

### `ItemCategoriesConfig`

二手交易分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

- `categories`：array[string]，可选。

### `ItemCreate`

- `title`：string，必填。
- `description`：string，可选。
- `price`：integer，可选。单位：分
- `category`：string，可选。
- `images`：array[ItemImageIn]，可选。
  - `object_key`：string，必填。
  - `sort_order`：integer，可选。

### `ItemDescriptionRequest`

闲置物品描述 AI 润色。

- `title`：string，必填。
- `category`：string，必填。

### `ItemImageIn`

- `object_key`：string，必填。
- `sort_order`：integer，可选。

### `ItemImageOut`

- `id`：string(uuid)，必填。
- `object_key`：string，必填。
- `sort_order`：integer，必填。

### `ItemOut`

- `id`：string(uuid)，必填。
- `owner_id`：string，必填。
- `title`：string，必填。
- `description`：string，必填。
- `price`：integer，必填。
- `category`：string，必填。
- `status`：integer，必填。
- `images`：array[ItemImageOut]，可选。
  - `id`：string(uuid)，必填。
  - `object_key`：string，必填。
  - `sort_order`：integer，必填。
- `created_at`：string | null，可选。

### `ItemReviewConfig`

二手物品发布审核开关（DB 值覆盖 school.yaml 默认值）。

- `enabled`：boolean，可选。

### `ItemReviewRejectRequest`

拒绝审核时的原因说明。

- `reason`：string，可选。

### `ItemUpdate`

- `title`：string | null，可选。
- `description`：string | null，可选。
- `price`：integer | null，可选。
- `category`：string | null，可选。
- `status`：integer | null，可选。状态流转目标值

### `JobApplicationCreate`

- `note`：string，可选。

### `JobApplicationOut`

- `id`：string(uuid)，必填。
- `job_id`：string，必填。
- `applicant_id`：string，必填。
- `status`：integer，必填。
- `note`：string，必填。

### `JobCategoriesConfig`

兼职岗位分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

- `categories`：array[string]，可选。

### `JobCreate`

- `title`：string，必填。
- `description`：string，可选。
- `company`：string，可选。
- `salary`：integer，可选。
- `category`：string，可选。

### `JobOut`

- `id`：string(uuid)，必填。
- `poster_id`：string，必填。
- `title`：string，必填。
- `description`：string，必填。
- `company`：string，必填。
- `salary`：integer，必填。
- `category`：string，必填。
- `status`：integer，必填。

### `JoinRequest`

- `role`：string，可选。

### `LoginRequest`

- `username`：string | null，可选。
- `account`：string | null，可选。
- `password`：string，必填。

### `PhoneLoginRequest`

- `target`：string，必填。
- `code`：string，必填。

### `ProfileUpdateRequest`

- `nickname`：string | null，可选。
- `avatar`：string | null，可选。
- `bio`：string | null，可选。
- `school_major`：string | null，可选。
- `campus`：string | null，可选。
- `contact_wx`：string | null，可选。
- `grade`：integer | null，可选。

### `ReadRequest`

- `last_read_message_id`：string | null，可选。

### `RefreshRequest`

- `refresh_token`：string，必填。

### `RegisterRequest`

- `username`：string，必填。
- `password`：string，必填。
- `email`：string | null，可选。
- `phone`：string | null，可选。
- `nickname`：string | null，可选。

### `ReportCreate`

- `target_type`：string，必填。user/item/message/comment/share
- `target_id`：string，必填。
- `reason`：string，必填。

### `ReportHandle`

- `action`：string，必填。resolve/reject/ban
- `note`：string，可选。

### `ReportLogOut`

- `id`：string(uuid)，必填。
- `operator_id`：string，必填。
- `action`：string，必填。
- `note`：string，必填。

### `ReportOut`

- `id`：string(uuid)，必填。
- `reporter_id`：string，必填。
- `target_type`：string，必填。
- `target_id`：string，必填。
- `reason`：string，必填。
- `status`：integer，必填。
- `handled_by`：string | null，可选。
- `logs`：array[ReportLogOut]，可选。
  - `id`：string(uuid)，必填。
  - `operator_id`：string，必填。
  - `action`：string，必填。
  - `note`：string，必填。

### `SendCodeOut`

发送验证码响应。开发/测试模式（debug=true）返回 debug_code 便于本地验证；
生产环境 debug_code 恒为 null，验证码只能通过邮件/短信真实送达。

- `debug_code`：string | null，可选。
- `expires_in`：integer，可选。

### `SendCodeRequest`

- `target`：string，必填。手机号或邮箱
- `purpose`：string，可选。login/register/email
- `captcha_ticket`：string | null，可选。滑块验证票据（captcha_enabled 时必填，由 /captcha/verify 签发）

### `ShareCategoriesConfig`

学术资料分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

- `categories`：array[string]，可选。

### `ShareCreate`

- `title`：string，必填。
- `description`：string，可选。
- `file_key`：string，可选。
- `category`：string，可选。

### `ShareOut`

- `id`：string(uuid)，必填。
- `owner_id`：string，必填。
- `title`：string，必填。
- `description`：string，必填。
- `file_key`：string，必填。
- `category`：string，必填。
- `downloads`：integer，必填。
- `download_url`：string | null，可选。

### `SliderCaptchaOut`

滑块验证载荷：两张 base64 图片 + 画布尺寸。

注意：缺口的**横坐标不会下发**（仅服务端保存），只有纵坐标 y 需要下发，
前端据此把滑块放在同一水平线上。

- `token`：string，必填。本次验证令牌，校验时回传
- `background`：string，必填。带缺口的背景图（data URI）
- `slider`：string，必填。拼图块（data URI，透明 PNG）
- `width`：integer，必填。画布宽度（px）
- `height`：integer，必填。画布高度（px）
- `slider_size`：integer，必填。滑块边长（px）
- `y`：integer，必填。缺口纵坐标（px），滑块需保持同一水平线
- `expires_in`：integer，必填。令牌有效期（秒）

### `SliderVerifyOut`

校验通过后的票据，需在调用 send-code 时回传（一次性）。

- `ticket`：string，必填。
- `expires_in`：integer，必填。

### `SliderVerifyRequest`

- `token`：string，必填。generate_slider 返回的令牌
- `offset_x`：number，必填。滑块相对画布左边缘的位移（px）
- `track`：array[array[number]]，可选。拖动轨迹 [[t_ms, x, y], ...]，用于识别脚本行为
- `elapsed_ms`：integer，可选。从开始拖到松手的总耗时（毫秒）

### `StallCreate`

- `canteen_id`：string，必填。
- `name`：string，必填。
- `image`：string，可选。

### `StallOut`

- `id`：string(uuid)，必填。
- `canteen_id`：string，必填。
- `name`：string，必填。
- `image`：string，必填。
- `dishes`：array[DishOut]，可选。
  - `id`：string(uuid)，必填。
  - `stall_id`：string，必填。
  - `name`：string，必填。
  - `price`：integer，必填。
  - `image`：string，必填。

### `TeamCreate`

- `title`：string，必填。
- `description`：string，可选。
- `required_roles`：string，可选。
- `category`：string，可选。
- `max_members`：integer，可选。
- `contact_info`：string，可选。

### `TeamMemberOut`

- `id`：string(uuid)，必填。
- `team_id`：string，必填。
- `user_id`：string，必填。
- `role`：string，必填。
- `status`：integer，必填。

### `TeamOut`

- `id`：string(uuid)，必填。
- `creator_id`：string，必填。
- `title`：string，必填。
- `description`：string，必填。
- `required_roles`：string，必填。
- `status`：integer，必填。
- `category`：string，可选。
- `max_members`：integer，可选。
- `contact_info`：string，可选。
- `member_count`：integer，可选。

### `TeammateCategoriesConfig`

搭子组队分类列表（后台可动态配置，DB 值覆盖 school.yaml 默认值）。

- `categories`：array[string]，可选。

### `TokenResponse`

- `access_token`：string，必填。
- `refresh_token`：string，必填。
- `token_type`：string，可选。
- `expires_in`：integer，必填。

### `TradeSessionOut`

- `id`：string(uuid)，必填。
- `item_id`：string，必填。
- `buyer_id`：string，必填。
- `seller_id`：string，必填。
- `status`：integer，必填。
- `conversation_id`：string | null，可选。

### `UnbindOAuthRequest`

- `provider`：string，必填。wechat/qq

### `UserOut`

- `id`：string(uuid)，必填。
- `username`：string，必填。
- `email`：string | null，可选。
- `phone`：string | null，可选。
- `nickname`：string，必填。
- `avatar`：string | null，可选。
- `status`：integer，必填。
- `created_at`：string(date-time)，必填。

### `UserProfileOut`

- `id`：string(uuid)，必填。
- `user_id`：string，必填。
- `username`：string，必填。
- `nickname`：string，必填。
- `avatar`：string | null，可选。
- `bio`：string，必填。
- `school_major`：string，必填。
- `campus`：string，必填。
- `contact_wx`：string，必填。
- `grade`：integer，必填。
- `verified`：boolean，必填。
- `email`：string | null，可选。
- `phone`：string | null，可选。

### `ValidationError`

- `loc`：array[string | integer]，必填。
- `msg`：string，必填。
- `type`：string，必填。
- `input`：any，可选。
- `ctx`：object，可选。

### `VerifyEmailRequest`

- `token`：string，必填。邮箱验证 JWT

---

## admin

### DELETE `/api/admin/canteens/{canteen_id}` — Admin Delete Canteen

删除食堂（级联删除档口、菜品与评价）。

**请求参数**

- `canteen_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### DELETE `/api/admin/canteens/stalls/{stall_id}` — Admin Delete Stall

**请求参数**

- `stall_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### DELETE `/api/admin/canteens/dishes/{dish_id}` — Admin Delete Dish

**请求参数**

- `dish_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### DELETE `/api/admin/items/{item_id}` — Admin Delete Item View

Soft-delete any item. Bypasses owner check.

**请求参数**

- `item_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### DELETE `/api/admin/files/orphans` — Admin Cleanup Orphan Files View

删除全部孤儿文件，返回实际删除数量。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/me` — Me

**响应**

- `200`：Successful Response — `ApiResponse_AdminOut_`

### GET `/api/admin/dashboard` — Dashboard View

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/users` — Users

**请求参数**

- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/auth/email-config` — Get Email Config

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_EmailRegisterConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/reports` — Reports

**请求参数**

- `status`（查询，可选）：integer。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/items` — Admin List Items

List all items (any user's) with optional status filter and pagination.

**请求参数**

- `status`（查询，可选）：integer。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/items/review-config` — Admin Get Item Review

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_ItemReviewConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/items/categories` — Admin Get Item Categories

读取二手交易分类（后台配置）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_ItemCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/courses/departments` — Admin Get Course Departments

读取课程开课院系列表（后台配置）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_CourseDepartmentsConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/courses/departments/groups` — Admin Get Course Department Groups

读取课程院系的**学部分组**（后台可配置，前端两级筛选的数据源）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_CourseDepartmentGroupsConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/jobs/categories` — Admin Get Job Categories

读取兼职岗位分类（后台配置）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_JobCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/shares/categories` — Admin Get Share Categories

读取学术资料分类（后台配置）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_ShareCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/teammates/categories` — Admin Get Teammate Categories

读取搭子组队分类（后台配置）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_TeammateCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/canteens/config` — Admin Get Canteen Config

读取食堂维度枚举（学部 / 餐饮区 / 类型 / 学期）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenConfig_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/ai/config` — Admin Get Ai Config

读取 AI 助手开关与运行状态（含 API Key 配置提示，不回传 Key 本身）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/canteens` — Admin List Canteens

食堂管理列表（含档口与菜品）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_list_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/files/orphans` — Admin List Orphan Files View

扫描存储中未被任何业务记录引用的孤儿文件（只列出，不删除）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### PATCH `/api/admin/items/{item_id}` — Admin Update Item View

Update any item's fields (e.g., take off sale). Bypasses owner check.

**请求参数**

- `item_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `title`：string | null，可选。
- `description`：string | null，可选。
- `price`：integer | null，可选。
- `category`：string | null，可选。
- `status`：integer | null，可选。状态流转目标值

**响应**

- `200`：Successful Response — `ApiResponse_ItemOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/discover` — Discover

用网关密钥换取短时网关令牌（HMAC）。密钥错误一律 404，避免暴露管理端存在。

**请求体**

> 必填

- `gateway_key`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/login` — Login

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `username`：string，必填。
- `password`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_AdminTokenResponse_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/users/{user_id}/ban` — Ban

**请求参数**

- `user_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `reason`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/users/{user_id}/unban` — Unban

**请求参数**

- `user_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/users/{user_id}/promote` — Promote

将普通用户提升为管理员（设置其后台登录密码），并标记 User.is_admin。

**请求参数**

- `user_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `password`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/canteens` — Admin Create Canteen

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `name`：string，必填。
- `location`：string，可选。
- `image`：string，可选。
- `campus`：string，可选。
- `zone`：string，可选。
- `canteen_type`：string，可选。
- `floor`：string，可选。
- `description`：string，可选。
- `features`：array[string]，可选。
- `popular_dishes`：array[string]，可选。
- `opening_hours`：string，可选。
- `semester`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/canteens/stalls` — Admin Create Stall

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `canteen_id`：string，必填。
- `name`：string，必填。
- `image`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_StallOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/canteens/dishes` — Admin Create Dish

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，可选。单位：分
- `image`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_DishOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/items/{item_id}/approve` — Admin Approve Item View

审核通过：待审核(PENDING) -> 上架(ON_SALE)。

**请求参数**

- `item_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_ItemOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/items/{item_id}/reject` — Admin Reject Item View

审核拒绝：待审核(PENDING) -> 下架(OFF_SHELF)。

**请求参数**

- `item_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `reason`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ItemOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/config/reload` — Reload School Config

重读 ``config/school.yaml`` 并广播到所有实例（零停机热更新）。

适用场景：运维直接修改了服务器上的 school.yaml（学校名称、域名白名单、
业务规则阈值等静态配置），希望**不重启**就让全校实例生效。

实现：向 Redis ``config:reload`` 频道发布消息，各实例的长驻监听 Task
收到后原地刷新 ``Settings`` 单例。发布者自身也在订阅者之列，
因此本实例同样会刷新。

Redis 不可用（``receivers == 0``）时降级为**仅本机刷新**并置
``degraded=true`` —— 让运维立刻看到"热更新没广播出去"，
而不是误以为全集群已生效。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/auth/email-config` — Put Email Config

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `enabled`：boolean，可选。
- `domains`：array[string]，可选。
- `pattern`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_EmailRegisterConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/items/review-config` — Admin Put Item Review

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `enabled`：boolean，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ItemReviewConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/items/categories` — Admin Put Item Categories

更新二手交易分类（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `categories`：array[string]，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ItemCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/courses/departments` — Admin Put Course Departments

更新课程开课院系列表（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `departments`：array[string]，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CourseDepartmentsConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/courses/departments/groups` — Admin Put Course Department Groups

更新课程院系学部分组（写 DB，实时生效）。

传空数组即可回到"扁平院系"模式（前端降级为单排 pill）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `groups`：array[DepartmentGroup]，可选。
  - `group`：string，必填。
  - `departments`：array[string]，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CourseDepartmentGroupsConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/jobs/categories` — Admin Put Job Categories

更新兼职岗位分类（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `categories`：array[string]，可选。

**响应**

- `200`：Successful Response — `ApiResponse_JobCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/shares/categories` — Admin Put Share Categories

更新学术资料分类（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `categories`：array[string]，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ShareCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/teammates/categories` — Admin Put Teammate Categories

更新搭子组队分类（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `categories`：array[string]，可选。

**响应**

- `200`：Successful Response — `ApiResponse_TeammateCategoriesConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/canteens/config` — Admin Put Canteen Config

更新食堂维度枚举（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `campuses`：array[string]，可选。
- `zones`：object，可选。
- `types`：array[string]，可选。
- `semesters`：array[string]，可选。
- `current_semester`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/ai/config` — Admin Put Ai Config

更新 AI 助手开关与模型名（写 DB，实时生效）。

**请求参数**

- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `enabled`：boolean，可选。
- `model`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_AiFeatureConfig_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/canteens/{canteen_id}` — Admin Update Canteen

**请求参数**

- `canteen_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `name`：string，必填。
- `location`：string，可选。
- `image`：string，可选。
- `campus`：string，可选。
- `zone`：string，可选。
- `canteen_type`：string，可选。
- `floor`：string，可选。
- `description`：string，可选。
- `features`：array[string]，可选。
- `popular_dishes`：array[string]，可选。
- `opening_hours`：string，可选。
- `semester`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenOut_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/canteens/stalls/{stall_id}` — Admin Update Stall

**请求参数**

- `stall_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `canteen_id`：string，必填。
- `name`：string，必填。
- `image`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_StallOut_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/canteens/dishes/{dish_id}` — Admin Update Dish

**请求参数**

- `dish_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，可选。单位：分
- `image`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_DishOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## ai

### GET `/api/ai/status` — Ai Status

AI 功能开关状态（公开）：前端据此条件渲染 AI 入口。

**响应**

- `200`：Successful Response — `ApiResponse_AiStatusOut_`

### POST `/api/ai/insights` — Insights

首页校园智能灵感。

**请求体**

> 必填

- `topic`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/ai/item-description` — Item Description

闲置发布描述 AI 润色。

**请求体**

> 必填

- `title`：string，必填。
- `category`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/ai/course-summary` — Course Summary

课程评价 AI 汇总。

**请求体**

> 必填

- `reviewTexts`：array[string]，必填。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/ai/categorize` — Categorize

内容自动分类与安全预审（发帖场景预留）。

**请求体**

> 必填

- `content`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_CategorizeOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## audit

### GET `/api/admin/audit-logs` — Get Audit Logs

分页查询审计日志，按时间倒序。

**请求参数**

- `action`（查询，可选）：string | null。按动作过滤
- `actor_id`（查询，可选）：string | null。按操作者 ID 过滤
- `actor_type`（查询，可选）：string | null。user/admin/system/anonymous
- `result`（查询，可选）：string | null。success/failure
- `keyword`（查询，可选）：string | null。按账号/IP/动作模糊搜索
- `limit`（查询，可选）：integer。
- `offset`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_AuditLogPage_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/audit-logs/actions` — Get Audit Actions

动作字典，供后台筛选下拉框使用（避免前端硬编码一份）。

**响应**

- `200`：Successful Response — `ApiResponse_list_AuditActionOption__`

---

## auth

### DELETE `/api/auth/unbind/email` — Unbind Email Endpoint

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`

### DELETE `/api/auth/unbind/phone` — Unbind Phone Endpoint

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`

### DELETE `/api/auth/unbind/oauth` — Unbind Oauth Endpoint

**请求体**

> 必填

- `provider`：string，必填。wechat/qq

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/auth/captcha/config` — Captcha Config

公开只读：验证码开关与当前生效的提供方，供前端决定渲染哪种验证。

``provider`` 取值：
  * ``geetest`` —— 已配置极验 captcha_id/key，前端渲染极验组件
  * ``builtin`` —— 未接入第三方，使用服务端生成的拼图滑块

前端只认这个字段，不自己判断"有没有极验"，
避免两端对同一份配置产生不同理解。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/auth/captcha/slider` — Captcha Slider

获取一次滑块验证（背景图 + 拼图块）。

缺口的横坐标只保存在服务端，响应中仅包含纵坐标 y，
前端据此把拼图块放在同一水平线上。

**响应**

- `200`：Successful Response — `ApiResponse_SliderCaptchaOut_`

### GET `/api/auth/email-config` — Email Register Config

公开只读：邮箱注册规则（是否开启 + 允许域名/正则），供注册页动态展示。

**响应**

- `200`：Successful Response — `ApiResponse_EmailRegisterConfig_`

### GET `/api/auth/wechat/state` — Wechat Oauth State

前端获取 state（防 CSRF）。

**响应**

- `200`：Successful Response — `ApiResponse_str_`

### GET `/api/auth/qq/state` — Qq Oauth State

**响应**

- `200`：Successful Response — `ApiResponse_str_`

### GET `/api/auth/wechat/callback` — Wechat Callback

**请求参数**

- `code`（查询，必填）：string。
- `state`（查询，可选）：string。

**响应**

- `200`：Successful Response — `ApiResponse_TokenResponse_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/auth/qq/callback` — Qq Callback

**请求参数**

- `code`（查询，必填）：string。
- `state`（查询，可选）：string。

**响应**

- `200`：Successful Response — `ApiResponse_TokenResponse_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/auth/bindings` — Get Bindings

查询当前账户的绑定方式（自定义账号/邮箱/手机号/第三方）。

**响应**

- `200`：Successful Response — `ApiResponse_BindingsOut_`

### POST `/api/auth/register` — Register User

**请求体**

> 必填

- `username`：string，必填。
- `password`：string，必填。
- `email`：string | null，可选。
- `phone`：string | null，可选。
- `nickname`：string | null，可选。

**响应**

- `200`：Successful Response — `ApiResponse_UserOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/login` — Login User

统一登录：账号（邮箱 / 手机号 / 自定义账号）+ 密码。

**请求体**

> 必填

- `username`：string | null，可选。
- `account`：string | null，可选。
- `password`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_TokenResponse_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/phone-login` — Phone Login User

**请求体**

> 必填

- `target`：string，必填。
- `code`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_TokenResponse_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/refresh` — Refresh User Token

**请求体**

> 必填

- `refresh_token`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_TokenResponse_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/logout` — Logout User

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`

### POST `/api/auth/captcha/geetest/verify` — Captcha Geetest Verify

极验二次校验：通过后签发一次性票据（供 send-code 使用）。

票据机制与自建滑块**完全一致**，因此下游 send-code 不需要区分
用户是通过哪种方式完成的验证 —— 换 provider 对业务代码透明。

**请求体**

> 必填

- `lot_number`：string，必填。验证流水号
- `captcha_output`：string，必填。验证输出信息
- `pass_token`：string，必填。验证通过标识
- `gen_time`：string，必填。验证通过时间戳

**响应**

- `200`：Successful Response — `ApiResponse_SliderVerifyOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/captcha/verify` — Captcha Verify

校验滑块拖动结果，通过则签发一次性票据（供 send-code 使用）。

**请求体**

> 必填

- `token`：string，必填。generate_slider 返回的令牌
- `offset_x`：number，必填。滑块相对画布左边缘的位移（px）
- `track`：array[array[number]]，可选。拖动轨迹 [[t_ms, x, y], ...]，用于识别脚本行为
- `elapsed_ms`：integer，可选。从开始拖到松手的总耗时（毫秒）

**响应**

- `200`：Successful Response — `ApiResponse_SliderVerifyOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/send-code` — Send Verification Code

发送验证码（邮箱/手机号，purpose 区分用途）。

开启滑块验证时，必须携带 ``/captcha/verify`` 签发的一次性票据，
否则拒绝发送——避免脚本绕过滑块直接刷验证码轰炸邮箱/手机。

默认**绝不**回传验证码（仅通过邮件送达）；
仅当开启 ``EXPOSE_VERIFICATION_CODE`` 时回传 debug_code，供本地联调与自动化测试使用。

**请求体**

> 必填

- `target`：string，必填。手机号或邮箱
- `purpose`：string，可选。login/register/email
- `captcha_ticket`：string | null，可选。滑块验证票据（captcha_enabled 时必填，由 /captcha/verify 签发）

**响应**

- `200`：Successful Response — `ApiResponse_SendCodeOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/verify-email` — Verify Email Endpoint

**请求体**

> 必填

- `token`：string，必填。邮箱验证 JWT

**响应**

- `200`：Successful Response — `ApiResponse_UserOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/email-register` — Email Register

邮箱验证码注册：校验后台邮箱规则 + 验证码，自动生成自定义账号并签发令牌（注册即登录）。

**请求体**

> 必填

- `email`：string(email)，必填。
- `password`：string，必填。
- `nickname`：string | null，可选。
- `code`：string，必填。邮箱验证码（purpose=register）

**响应**

- `200`：Successful Response — `ApiResponse_EmailRegisterResponse_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/bind/email` — Bind Email Endpoint

补充绑定邮箱（需邮箱验证码，purpose=bind_email）。

**请求体**

> 必填

- `email`：string(email)，必填。
- `code`：string，必填。邮箱验证码（purpose=bind_email）

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/bind/phone` — Bind Phone Endpoint

补充绑定手机号（需短信验证码，purpose=bind_phone）。

**请求体**

> 必填

- `phone`：string，必填。
- `code`：string，必填。短信验证码（purpose=bind_phone）

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/bind/oauth` — Bind Oauth Endpoint

补充绑定 QQ / 微信（需 OAuth 授权码 + state 防 CSRF）。

**请求体**

> 必填

- `provider`：string，必填。wechat/qq
- `code`：string，必填。
- `redirect_uri`：string，可选。
- `state`：string | null，可选。OAuth state（防 CSRF）

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

---

## canteen

### GET `/api/canteens/configs` — Canteen Configs

公开读取食堂维度枚举（学部 / 餐饮区 / 类型 / 学期）。

前端首页 Tab、筛选 chip 的数据源，全部由后台 ``canteen.config`` 下发，
不再写死常量。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/canteens` — List All

**请求参数**

- `campus`（查询，可选）：string。
- `zone`（查询，可选）：string。
- `canteen_type`（查询，可选）：string。
- `semester`（查询，可选）：string。
- `keyword`（查询，可选）：string。

**响应**

- `200`：Successful Response — `ApiResponse_list_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/canteens/dishes/{dish_id}` — Dish Detail

**请求参数**

- `dish_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/canteens/{canteen_id}` — Detail

**请求参数**

- `canteen_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/canteens/dishes/{dish_id}/reviews` — Review

**请求参数**

- `dish_id`（路径，必填）：string。

**请求体**

> 必填

- `rating`：integer，可选。
- `content`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenReviewOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## course

### GET `/api/courses` — List All

**请求参数**

- `keyword`（查询，可选）：string。
- `department`（查询，可选）：string。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/courses/departments` — Departments

公开读取课程院系列表（后台配置，含 school.yaml 兜底）。

响应同时给出两种结构，前端按能力渐进使用：

- ``departments``：扁平列表（老前端 / 后端筛选直接可用）；
- ``groups``：按学部分组的二级结构 ``[{group, departments}]``，
  配了分组才有内容，为空时前端降级为单排 pill。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/courses/{course_id}` — Detail

**请求参数**

- `course_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/courses` — Create

**请求体**

> 必填

- `code`：string，必填。
- `name`：string，必填。
- `teacher`：string，可选。
- `credits`：integer，可选。
- `semester`：string，可选。
- `department`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CourseOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/courses/{course_id}/reviews` — Review

**请求参数**

- `course_id`（路径，必填）：string。

**请求体**

> 必填

- `rating`：integer，可选。
- `content`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CourseReviewOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## files

### GET `/api/files/raw` — Raw

本地降级模式下载文件。

**请求参数**

- `key`（查询，必填）：string。

**响应**

- `200`：Successful Response
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/files/presign` — Presign

**请求体**

> Content-Type: `application/x-www-form-urlencoded`

- `prefix`：string，可选。
- `filename`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/files/upload` — Upload

**请求体**

> 必填

> Content-Type: `multipart/form-data`

- `key`：string，必填。
- `file`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

---

## item

### DELETE `/api/items/{item_id}` — Delete

删除物品：本人（write）或管理员（admin）可删。

权限判定完全由 ``require_scope`` + ``require_owner_or_scope`` 表达，
Service 层的 ``delete_item`` 只负责删除，不知道"管理员"这个概念的存在。

**请求参数**

- `item_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/items` — List All

**请求参数**

- `keyword`（查询，可选）：string。
- `category`（查询，可选）：string。
- `status`（查询，可选）：integer。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/items/search` — Search

**请求参数**

- `q`（查询，可选）：string。
- `limit`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_list_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/items/categories` — Categories

公开读取二手交易分类（后台配置，含 school.yaml 兜底）。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/items/{item_id}` — Detail

**请求参数**

- `item_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_ItemOut_`
- `422`：Validation Error — `HTTPValidationError`

### PATCH `/api/items/{item_id}` — Update

**请求参数**

- `item_id`（路径，必填）：string。

**请求体**

> 必填

- `title`：string | null，可选。
- `description`：string | null，可选。
- `price`：integer | null，可选。
- `category`：string | null，可选。
- `status`：integer | null，可选。状态流转目标值

**响应**

- `200`：Successful Response — `ApiResponse_ItemOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/items` — Create

**请求体**

> 必填

- `title`：string，必填。
- `description`：string，可选。
- `price`：integer，可选。单位：分
- `category`：string，可选。
- `images`：array[ItemImageIn]，可选。
  - `object_key`：string，必填。
  - `sort_order`：integer，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ItemOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/items/{item_id}/trade` — Trade

**请求参数**

- `item_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_TradeSessionOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## job

### GET `/api/jobs/categories` — Categories

公开读取兼职岗位分类（后台配置，含 school.yaml 兜底）。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/jobs` — List All

**请求参数**

- `keyword`（查询，可选）：string。
- `status`（查询，可选）：integer。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/jobs/{job_id}/applications` — Applications

**请求参数**

- `job_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_list_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/jobs` — Create

**请求体**

> 必填

- `title`：string，必填。
- `description`：string，可选。
- `company`：string，可选。
- `salary`：integer，可选。
- `category`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_JobOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/jobs/{job_id}/apply` — Apply

**请求参数**

- `job_id`（路径，必填）：string。

**请求体**

> 必填

- `note`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_JobApplicationOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## launcher

### GET `/api/health` — Health

健康检查：返回服务与基础依赖状态。

同时挂在 /health 与 /api/health 两个路径上。
后者不是冗余：前端 dev server（frontend/server.ts）本地实现了
``/api/health`` 并直接返回 200，而生产由 nginx 统一转发 /api/* 到后端 ——
若后端不提供该路径，同一个探测就会在开发环境 200、上线后 404。
e2e 的 webServer 健康检查用的正是 ``${BACKEND_URL}/api/health``。

**响应**

- `200`：Successful Response — `object`

### GET `/health` — Health

健康检查：返回服务与基础依赖状态。

同时挂在 /health 与 /api/health 两个路径上。
后者不是冗余：前端 dev server（frontend/server.ts）本地实现了
``/api/health`` 并直接返回 200，而生产由 nginx 统一转发 /api/* 到后端 ——
若后端不提供该路径，同一个探测就会在开发环境 200、上线后 404。
e2e 的 webServer 健康检查用的正是 ``${BACKEND_URL}/api/health``。

**响应**

- `200`：Successful Response — `object`

### GET `/metrics` — Metrics

Prometheus 指标端点。

**响应**

- `200`：Successful Response

---

## message

### GET `/api/messages/conversations` — Conversations

**响应**

- `200`：Successful Response — `ApiResponse_list_`

### GET `/api/messages/conversations/{conversation_id}` — History

**请求参数**

- `conversation_id`（路径，必填）：string。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/messages/unread` — Unread

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### POST `/api/messages/conversations/{conversation_id}/read` — Read

**请求参数**

- `conversation_id`（路径，必填）：string。

**请求体**

> 必填

- `last_read_message_id`：string | null，可选。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

---

## report

### GET `/api/reports` — List All

**请求参数**

- `status`（查询，可选）：integer。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。
- `X-Admin-Gateway`（头，可选）：string | null。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/reports` — Submit

**请求体**

> 必填

- `target_type`：string，必填。user/item/message/comment/share
- `target_id`：string，必填。
- `reason`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_ReportOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/reports/{report_id}/handle` — Handle

**请求参数**

- `report_id`（路径，必填）：string。
- `X-Admin-Gateway`（头，可选）：string | null。

**请求体**

> 必填

- `action`：string，必填。resolve/reject/ban
- `note`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ReportOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## share

### GET `/api/shares/categories` — Categories

公开读取学术资料分类（后台配置，含 school.yaml 兜底）。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/shares` — List All

**请求参数**

- `category`（查询，可选）：string。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/shares/{share_id}/download` — Download

**请求参数**

- `share_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/shares` — Create

**请求体**

> 必填

- `title`：string，必填。
- `description`：string，可选。
- `file_key`：string，可选。
- `category`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ShareOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## teammate

### GET `/api/teams/categories` — Categories

公开读取搭子组队分类（后台配置，含 school.yaml 兜底）。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/teams` — List All

**请求参数**

- `category`（查询，可选）：string。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/teams/{team_id}` — Detail

**请求参数**

- `team_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/teams` — Create

**请求体**

> 必填

- `title`：string，必填。
- `description`：string，可选。
- `required_roles`：string，可选。
- `category`：string，可选。
- `max_members`：integer，可选。
- `contact_info`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_TeamOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/teams/{team_id}/join` — Join

**请求参数**

- `team_id`（路径，必填）：string。

**请求体**

> 必填

- `role`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_TeamMemberOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## user

### GET `/api/users/me` — Get Me

**响应**

- `200`：Successful Response — `ApiResponse_UserProfileOut_`

### GET `/api/users` — List All

**请求参数**

- `q`（查询，可选）：string。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/users/search` — Search

**请求参数**

- `q`（查询，可选）：string。
- `limit`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_list_`
- `422`：Validation Error — `HTTPValidationError`

### PATCH `/api/users/me` — Update Me

**请求体**

> 必填

- `nickname`：string | null，可选。
- `avatar`：string | null，可选。
- `bio`：string | null，可选。
- `school_major`：string | null，可选。
- `campus`：string | null，可选。
- `contact_wx`：string | null，可选。
- `grade`：integer | null，可选。

**响应**

- `200`：Successful Response — `ApiResponse_UserProfileOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## 默认

### GET `/` — Root

**响应**

- `200`：Successful Response — `object`

---
