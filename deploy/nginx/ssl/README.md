# TLS 证书放置目录

`nginx.conf` 已启用 HTTPS（`listen 443 ssl; http2 on;`），并通过
`deploy/docker-compose.yml` 把本目录**只读**挂载到容器内的 `/etc/nginx/ssl`。

## 没有证书也能启动（自动降级）

`docker-compose.yml` 里有一个 `cert-init` 服务，**在 nginx 启动前**检查本目录：

| 情况 | 行为 |
|------|------|
| 已存在 `fullchain.pem` + `privkey.pem` | 原样使用，不改动 |
| 两者任一缺失 | **自动生成自签名证书**（`CN=localhost`，有效期 365 天） |

因此 `docker compose up` **永远不会因为缺证书而卡住**——HTTPS 链路可先跑通，
便于确认反向代理、WebSocket、静态托管是否正常工作。

> ⚠️ 自签名证书会导致浏览器显示"连接不安全"。
> 它**只用于联调**，生产上线前必须替换为真实证书（见下），
> 否则用户会遇到证书告警，且 HTTPS 的安全承诺形同虚设。

## 放置真实证书

把证书文件命名为以下两个名字放进本目录即可，**无需修改任何配置**：

| 文件名 | 说明 |
|--------|------|
| `fullchain.pem` | 服务端证书 + 中级证书链（Let's Encrypt `fullchain.pem`） |
| `privkey.pem`   | 私钥（Let's Encrypt `privkey.pem`） |

nginx 配置中对应的引用：

```nginx
ssl_certificate     /etc/nginx/ssl/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/privkey.pem;
```

> 注意：`cert-init` 只在**两个文件都齐全**时才跳过生成。
> 若只放了其中一个，仍会被判定为缺失并重新生成——请确保两个文件同名齐备。

## 证书来源（任选其一）

1. **Let's Encrypt / certbot**（推荐，免费自动续期）
   ```bash
   certbot certonly --webroot -w /path/to/webroot -d your.domain.edu.cn
   # 续期后把 live/ 下的文件拷贝/软链到本目录
   cp /etc/letsencrypt/live/your.domain.edu.cn/fullchain.pem ./
   cp /etc/letsencrypt/live/your.domain.edu.cn/privkey.pem   ./
   ```
2. **自有 CA / 商业证书**（如学校信息中心签发）：按上述命名放置即可。

## 安全注意

- 本目录的 `*.pem` 已被 `.gitignore` 忽略（`deploy/nginx/ssl/*.pem`），**切勿提交私钥**。
- 仅挂载为只读（`:ro`），防止容器内进程改写证书。
- `nginx.conf` 已下发 HSTS 头（`max-age=31536000; includeSubDomains`），部署后全站强制 HTTPS。

## 不需要 HTTPS 的临时联调

若只想用 HTTP 快速验证（例如还没确定域名），可绕过证书环节：

```bash
NGINX_CONF=./nginx/nginx.http-only.conf docker compose -f deploy/docker-compose.yml up -d
```

该配置**不启用 TLS**，登录凭据与 Token 会明文传输，仅限内网或首次联调。
