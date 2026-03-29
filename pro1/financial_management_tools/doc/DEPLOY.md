# 生产环境部署指南

## 部署架构

```
用户 → Nginx (HTTPS, 443端口) → FastAPI (本地8081)
     ↓
   域名解析
```

## 部署步骤

### 1. 域名配置

- 购买域名
- 配置 DNS 解析到服务器 IP
- 如使用国内服务器，需要备案

### 2. Nginx 安装与配置

```bash
# 安装 Nginx
sudo apt update
sudo apt install nginx

# 配置 Nginx
sudo vim /etc/nginx/sites-available/finance-app
```

配置文件示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 替换为你的域名

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    # 静态文件（直接由 Nginx 处理，性能更好）
    location /static/ {
        alias /date_sdb/soft/openclaw/code/static/;
        expires 30d;
    }

    # API 请求转发到 FastAPI
    location / {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/finance-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. 获取 SSL 证书（Let's Encrypt 免费）

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

### 4. 配置 systemd 服务（开机自启）

```bash
sudo vim /etc/systemd/system/finance-app.service
```

```ini
[Unit]
Description=Finance App
After=network.target

[Service]
User=yzx
WorkingDirectory=/date_sdb/soft/openclaw/code
ExecStart=/date_sdb/tool/anaconda3/envs/finance/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable finance-app
sudo systemctl start finance-app

# 管理命令
sudo systemctl status finance-app   # 查看状态
sudo systemctl restart finance-app  # 重启
sudo systemctl stop finance-app     # 停止
```

### 5. 配置防火墙

```bash
# 开放端口
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 22    # SSH
sudo ufw enable
```

## 部署检查清单

- [ ] 域名解析生效
- [ ] Nginx 运行正常
- [ ] SSL 证书有效
- [ ] FastAPI 服务自启
- [ ] 防火墙开放端口
- [ ] 数据库备份定时任务

## 常用命令

```bash
# 查看服务状态
sudo systemctl status nginx
sudo systemctl status finance-app

# 重启服务
sudo systemctl restart nginx
sudo systemctl restart finance-app

# 查看日志
sudo journalctl -u finance-app -f
sudo tail -f /var/log/nginx/error.log

# 更新代码后
cd /date_sdb/soft/openclaw/code
git pull
sudo systemctl restart finance-app
```

## 性能优化（可选）

### 使用 Gunicorn 替代直接运行

```bash
pip install gunicorn

# 启动（多进程）
gunicorn -w 4 -b 127.0.0.1:8081 main:app
```

### 使用 uvicorn + gunicorn

```ini
# gunicorn.conf.py
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
```

## 备份策略

```bash
# 定时备份数据库
crontab -e

# 每天凌晨3点备份
0 3 * * * cp /date_sdb/soft/openclaw/code/database.db /backup/database_$(date +\%Y\%m\%d).db
```
