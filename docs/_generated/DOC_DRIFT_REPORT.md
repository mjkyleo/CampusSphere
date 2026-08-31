<!-- 本文件由 scripts/doc_sync.py 自动生成，请勿手工编辑 -->
# 文档漂移报告（自动生成）

> 生成时间：2026-08-31 04:31 UTC  ｜  来源：`scripts/doc_sync.py`

共发现 **7** 处漂移（⚠️ 需关注 1 项，ℹ️ 提示 6 项）。

## ⚠️ 需关注

- **[env_example_incomplete]** backend/.env.example 缺失以下可在 .env 中覆盖的配置键（建议补全以便部署者对照）：AUTH_RATE_LIMIT_PER_MINUTE、EXPOSE_VERIFICATION_CODE、SMTP_FROM、SMTP_TIMEOUT、SMTP_STARTTLS、GEETEST_CAPTCHA_ID、GEETEST_CAPTCHA_KEY、CODE_SEND_LIMIT_PER_MINUTE、MINIO、MEILISEARCH、ADMIN

## ℹ️ 提示

- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `APT_MIRROR`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `DOC_DRIFT_REPORT`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `MEILI_ENV`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `NGINX_CONF`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `PIP_INDEX_URL`，可能为过期配置键或拼写错误，请核对。
- **[stale_env_var]** 文档引用了未在 config.py / .env.example 中定义的环境变量 `PROJECT_STATUS`，可能为过期配置键或拼写错误，请核对。

---
建议：修正文档后重跑 `python scripts/doc_sync.py --check`，待无 warn 级漂移即可合入。
