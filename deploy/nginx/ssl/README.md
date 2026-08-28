# TLS 证书放置目录

`nginx.conf` 已启用 HTTPS（`listen 443 ssl; http2 on;`），并通过
`deploy/docker-compose.yml` 把本目录**只读**挂载到容器内的 `/etc/nginx/ssl`。

## 放置要求

将你的证书文件命名为以下两个名字放在这个目录里即可，无需改任何配置：

| 文件名 | 说明 |
|--------|------|
| `fullchain.pem` | 服务端证书 + 中级证书链（Let's Encrypt `fullchain.pem`） |
| `privkey.pem`   | 私钥（Let's Encrypt `privkey.pem`） |

nginx 配置中对应的引用：

```nginx
ssl_certificate     /etc/nginx/ssl/fullchain.pem;
ssl_certificate_key /etc/nginx/ssl/privkey.pem;
```

## 证书来源（任选其一）

1. **Let's Encrypt / certbot**（推荐，免费自动续期）
   ```bash
   certbot certonly --webroot -w ./frontend/dist -d your.domain.edu.cn
   # 续期后把 live/ 下的文件拷贝/软链到本目录
   cp /etc/letsencrypt/live/your.domain.edu.cn/fullchain.pem ./
   cp /etc/letsencrypt/live/your.domain.edu.cn/privkey.pem   ./
   ```
2. **自有 CA / 商业证书**：按上述命名放置即可。

## 安全注意

- 本目录的 `*.pem` 已被 `.gitignore` 忽略，**切勿提交私钥**。
- 仅挂载为只读（`:ro`），防止容器内进程改写证书。
- `nginx.conf` 已下发 HSTS 头（`max-age=31536000; includeSubDomains`），部署后全站强制 HTTPS。

## 自签名证书（仅本地/测试）

仅用于本地联调，浏览器会报不安全，不要用于生产：

```bash
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout privkey.pem -out fullchain.pem \
  -days 365 -subj "/CN=localhost"
```
