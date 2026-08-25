# campus-life-platform — API 接口文档

> 版本：`1.0.0` | 接口总数：73 | 生成时间：2026-08-25 16:29

> 约定：业务错误统一返回 **HTTP 200**，错误码在响应体 `code` 字段（如 40100 未认证 / 40300 禁止 / 40400 未找到 / 40900 冲突 / 42200 参数错误）。

## 目录

- [admin](#admin)
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

### `AdminLoginRequest`

- `username`：string，必填。
- `password`：string，必填。

### `AdminOut`

- `id`：string(uuid)，必填。
- `username`：string，必填。
- `role_id`：string | null，可选。
- `disabled`：boolean，可选。
- `permissions`：array[string]，可选。

### `AdminTokenResponse`

- `access_token`：string，必填。
- `refresh_token`：string，必填。
- `token_type`：string，可选。

### `ApiResponse_AdminOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AdminOut | null，可选。

### `ApiResponse_AdminTokenResponse_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：AdminTokenResponse | null，可选。

### `ApiResponse_BindingsOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：BindingsOut | null，可选。

### `ApiResponse_CanteenOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CanteenOut | null，可选。

### `ApiResponse_CanteenReviewOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：CanteenReviewOut | null，可选。

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

### `ApiResponse_ItemOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ItemOut | null，可选。

### `ApiResponse_JobApplicationOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：JobApplicationOut | null，可选。

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

### `ApiResponse_ShareOut_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：ShareOut | null，可选。

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

### `ApiResponse_str_`

- `code`：integer，可选。
- `message`：string，可选。
- `data`：string | null，可选。

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

### `CanteenCreate`

- `name`：string，必填。
- `location`：string，可选。

### `CanteenOut`

- `id`：string(uuid)，必填。
- `name`：string，必填。
- `location`：string，必填。
- `stalls`：array[StallOut]，可选。
  - `id`：string(uuid)，必填。
  - `canteen_id`：string，必填。
  - `name`：string，必填。
  - `dishes`：array[DishOut]，可选。
    - `id`：string(uuid)，必填。
    - `stall_id`：string，必填。
    - `name`：string，必填。
    - `price`：integer，必填。

### `CanteenReviewCreate`

- `rating`：integer，可选。
- `content`：string，可选。

### `CanteenReviewOut`

- `id`：string(uuid)，必填。
- `dish_id`：string，必填。
- `user_id`：string，必填。
- `rating`：integer，必填。
- `content`：string，必填。

### `CourseCreate`

- `code`：string，必填。
- `name`：string，必填。
- `teacher`：string，可选。
- `credits`：integer，可选。
- `semester`：string，可选。

### `CourseOut`

- `id`：string(uuid)，必填。
- `code`：string，必填。
- `name`：string，必填。
- `teacher`：string，必填。
- `credits`：integer，必填。
- `semester`：string，必填。

### `CourseReviewCreate`

- `rating`：integer，可选。
- `content`：string，可选。

### `CourseReviewOut`

- `id`：string(uuid)，必填。
- `course_id`：string，必填。
- `user_id`：string，必填。
- `rating`：integer，必填。
- `content`：string，必填。

### `DishCreate`

- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，可选。单位：分

### `DishOut`

- `id`：string(uuid)，必填。
- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，必填。

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

### `HTTPValidationError`

- `detail`：array[ValidationError]，可选。
  - `loc`：array[string | integer]，必填。
  - `msg`：string，必填。
  - `type`：string，必填。
  - `input`：any，可选。
  - `ctx`：object，可选。

### `ItemCreate`

- `title`：string，必填。
- `description`：string，可选。
- `price`：integer，可选。单位：分
- `category`：string，可选。
- `images`：array[ItemImageIn]，可选。
  - `object_key`：string，必填。
  - `sort_order`：integer，可选。

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

### `SendCodeRequest`

- `target`：string，必填。手机号或邮箱
- `purpose`：string，可选。login/register/email

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

### `StallCreate`

- `canteen_id`：string，必填。
- `name`：string，必填。

### `StallOut`

- `id`：string(uuid)，必填。
- `canteen_id`：string，必填。
- `name`：string，必填。
- `dishes`：array[DishOut]，可选。
  - `id`：string(uuid)，必填。
  - `stall_id`：string，必填。
  - `name`：string，必填。
  - `price`：integer，必填。

### `TeamCreate`

- `title`：string，必填。
- `description`：string，可选。
- `required_roles`：string，可选。

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
- `member_count`：integer，可选。

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

### GET `/api/admin/me` — Me

**响应**

- `200`：Successful Response — `ApiResponse_AdminOut_`

### GET `/api/admin/dashboard` — Dashboard View

**响应**

- `200`：Successful Response — `ApiResponse_dict_`

### GET `/api/admin/users` — Users

**请求参数**

- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### GET `/api/admin/auth/email-config` — Get Email Config

**响应**

- `200`：Successful Response — `ApiResponse_EmailRegisterConfig_`

### GET `/api/admin/reports` — Reports

**请求参数**

- `status`（查询，可选）：integer。
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/login` — Login

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

**请求体**

> 必填

- `reason`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/admin/users/{user_id}/unban` — Unban

**请求参数**

- `user_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### PUT `/api/admin/auth/email-config` — Put Email Config

**请求体**

> 必填

- `enabled`：boolean，可选。
- `domains`：array[string]，可选。
- `pattern`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_EmailRegisterConfig_`
- `422`：Validation Error — `HTTPValidationError`

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

### POST `/api/auth/send-code` — Send Verification Code

**请求体**

> 必填

- `target`：string，必填。手机号或邮箱
- `purpose`：string，可选。login/register/email

**响应**

- `200`：Successful Response — `ApiResponse_NoneType_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/verify-email` — Verify Email Endpoint

**请求体**

> 必填

- `token`：string，必填。邮箱验证 JWT

**响应**

- `200`：Successful Response — `ApiResponse_UserOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/auth/email-register` — Email Register

邮箱验证码注册：校验后台邮箱规则 + 验证码，自动生成自定义账号。

**请求体**

> 必填

- `email`：string(email)，必填。
- `password`：string，必填。
- `nickname`：string | null，可选。
- `code`：string，必填。邮箱验证码（purpose=register）

**响应**

- `200`：Successful Response — `ApiResponse_UserOut_`
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

### GET `/api/canteens` — List All

**响应**

- `200`：Successful Response — `ApiResponse_list_`

### GET `/api/canteens/dishes/{dish_id}` — Dish Detail

**请求参数**

- `dish_id`（路径，必填）：string。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/canteens` — Create

**请求体**

> 必填

- `name`：string，必填。
- `location`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_CanteenOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/canteens/stalls` — Create Stall Endpoint

**请求体**

> 必填

- `canteen_id`：string，必填。
- `name`：string，必填。

**响应**

- `200`：Successful Response — `ApiResponse_StallOut_`
- `422`：Validation Error — `HTTPValidationError`

### POST `/api/canteens/dishes` — Create Dish Endpoint

**请求体**

> 必填

- `stall_id`：string，必填。
- `name`：string，必填。
- `price`：integer，可选。单位：分

**响应**

- `200`：Successful Response — `ApiResponse_DishOut_`
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
- `page`（查询，可选）：integer。
- `page_size`（查询，可选）：integer。

**响应**

- `200`：Successful Response — `ApiResponse_dict_`
- `422`：Validation Error — `HTTPValidationError`

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

### GET `/health` — Health

健康检查：返回服务与基础依赖状态。

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

**请求体**

> 必填

- `action`：string，必填。resolve/reject/ban
- `note`：string，可选。

**响应**

- `200`：Successful Response — `ApiResponse_ReportOut_`
- `422`：Validation Error — `HTTPValidationError`

---

## share

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

### GET `/api/teams` — List All

**请求参数**

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
