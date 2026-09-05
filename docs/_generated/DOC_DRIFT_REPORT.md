<!-- 本文件由 scripts/doc_sync.py 自动生成，请勿手工编辑 -->
# 文档漂移报告（自动生成）

> 生成时间：2026-09-05 09:56 UTC  ｜  来源：`scripts/doc_sync.py`

共发现 **20** 处漂移（⚠️ 需关注 2 项，ℹ️ 提示 18 项）。

## ⚠️ 需关注

- **[env_example_incomplete]** backend/.env.example 缺失以下可在 .env 中覆盖的配置键（建议补全以便部署者对照）：AUTH_RATE_LIMIT_PER_MINUTE、SMTP_STARTTLS、MINIO、MEILISEARCH、ADMIN
- **[api_count_mismatch]** README 声明 88 个接口，API_Reference.md 实际抽取到 128 个，请核对更新。

## ℹ️ 提示

- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `ALLOWED_IMAGE_TYPES`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `APT_MIRROR`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `BACKEND_URL`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `CONFIG_RELOAD_CHANNEL`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `DEFAULT_MAX_ENTRIES`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `DOC_DRIFT_REPORT`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `FULLSUITE_EXIT`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `IN_PROGRESS`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `ITEM_CREATE`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `MAX_PRICE_CENTS`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `MEILI_ENV`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `NAMING_CONVENTION`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `NGINX_CONF`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `PIP_INDEX_URL`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `PROJECT_STATUS`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `PUBLIC_GET_PREFIXES`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `REFACTOR_DELIVERABLE`，可能为过期配置键或拼写错误，请核对。
- **[module_undocumented]** 后端模块 `audit`（别名：无）未在 README/usage.md 中提及。

---
建议：修正文档后重跑 `python scripts/doc_sync.py --check`，待无 warn 级漂移即可合入。
