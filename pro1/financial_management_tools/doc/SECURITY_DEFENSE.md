# Web 应用安全防护指南

本文档介绍如何应对常见的 Web 攻击，包括预防、检测和响应措施。

---

## 一、防御策略总览

```
┌─────────────────────────────────────────────────────────────┐
│                      安全防护体系                             │
├─────────────────────────────────────────────────────────────┤
│  预防 → 检测 → 响应 → 恢复                                    │
│   ↑       ↑       ↑       ↑                                  │
│  防火墙   日志    告警    备份                               │
│  WAF     监控    自动    熔断                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、具体防护措施

### 1. DDoS 攻击防护

**攻击特征：**
- 短时间内大量请求
- 特定接口被高频访问
- 服务器 CPU/内存飙升

**防护措施：**

| 措施 | 说明 | 实施难度 |
|------|------|----------|
| 频率限制 | 限制单IP请求频率 | ⭐ 简单 |
| CDN 加速 | 隐藏源站，分担流量 | ⭐⭐ 中等 |
| WAF | Web应用防火墙 | ⭐⭐⭐ 复杂 |
| 云防护 | DDoS 高防服务 | 💰 付费 |

**代码示例 - 简单频率限制：**

```python
from fastapi import Request, HTTPException
from collections import defaultdict
import time

# 简单内存实现（生产环境用 Redis）
request_counts = defaultdict(list)
RATE_LIMIT = 30  # 每分钟最大请求数
RATE_WINDOW = 60  # 时间窗口（秒）

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 排除健康检查等接口
    if request.url.path in ["/", "/health"]:
        return await call_next(request)
    
    client_ip = request.client.host
    
    now = time.time()
    # 清理过期记录
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < RATE_WINDOW]
    
    if len(request_counts[client_ip]) >= RATE_LIMIT:
        return HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    
    request_counts[client_ip].append(now)
    return await call_next(request)
```

---

### 2. SQL 注入防护

**攻击特征：**
- 异常 SQL 语法出现在日志中
- 数据库出现异常查询

**防护措施：**

| 措施 | 说明 | 状态 |
|------|------|------|
| 参数化查询 | 使用 ORM | ✅ 已采用 |
| 最小权限 | 数据库用户权限最小化 | ⚠️ 建议 |
| 输入验证 | 验证数据类型 | ⚠️ 建议 |

**实践：**
```python
# ✅ 正确：使用参数化查询
db.query(User).filter(User.name == username)

# ❌ 错误：字符串拼接
db.execute(f"SELECT * FROM users WHERE name = '{username}'")
```

---

### 3. XSS 跨站脚本防护

**攻击特征：**
- 用户输入包含 `<script>` 标签
- 异常 HTML 标签出现在页面

**防护措施：**

| 措施 | 说明 | 状态 |
|------|------|------|
| 输出转义 | 返回时转义 HTML | ⚠️ 建议 |
| CSP 头 | 内容安全策略 | ⚠️ 建议 |
| HttpOnly | Cookie 加锁 | ⚠️ 建议 |

**代码示例 - 添加 CSP：**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    add_http_alias=True,
)

# 或添加自定义中间.middleware("http")
async def add_security_headers(request:件
@app Request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response
```

---

### 4. 信息泄露防护

**攻击特征：**
- 错误堆栈暴露在页面
- 调试信息可被访问

**防护措施：**

| 措施 | 说明 | 状态 |
|------|------|------|
| 关闭调试 | 生产环境 reload=False | ⚠️ 需检查 |
| 错误页面 | 自定义错误页面 | ⚠️ 需实现 |
| 日志脱敏 | 敏感信息打码 | ⚠️ 建议 |

**代码示例 - 生产环境配置：**

```python
# main.py
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8081,
        reload=False,      # 生产环境关闭
        log_level="info",  # 日志级别
        access_log=False   # 关闭访问日志（可选）
    )
```

---

### 5. 接口防爬

**攻击特征：**
- 频繁访问数据接口
- 批量数据被获取

**防护措施：**

| 措施 | 说明 | 状态 |
|------|------|------|
| 验证码 | 访问频繁需验证 | ⚠️ 可选 |
| 数据加密 | 接口返回加密数据 | ⚠️ 可选 |
| 令牌验证 | 需携带有效令牌 | ⚠️ 可选 |

---

## 三、监控与检测

### 1. 请求日志

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url.path} - {request.client.host}")
    return await call_next(request)
```

### 2. 异常检测

| 监控项 | 阈值 | 动作 |
|--------|------|------|
| 请求量 | > 1000/分钟 | 告警 |
| 错误率 | > 5% | 告警 |
| 响应时间 | > 3秒 | 告警 |
| 特定IP | > 100/分钟 | 封禁 |

---

## 四、应急响应

### 攻击发生时的处理流程：

```
1. 发现异常
   ↓
2. 确认攻击类型
   ↓
3. 启动应急方案
   ↓
4. 阻断攻击
   ↓
5. 恢复服务
   ↓
6. 复盘改进
```

### 快速响应命令：

```bash
# 查看当前连接数
netstat -an | grep :8081 | wc -l

# 查看异常IP
netstat -an | grep :8081 | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn

# 封禁异常IP
iptables -I INPUT -s 1.2.3.4 -j DROP

# 解封
iptables -D INPUT -s 1.2.3.4 -j DROP
```

---

## 五、安全配置检查清单

### 生产环境部署前：

- [ ] 关闭调试模式 `reload=False`
- [ ] 设置合理的日志级别
- [ ] 配置请求频率限制
- [ ] 添加安全响应头
- [ ] 数据库账户权限最小化
- [ ] 定期备份数据库
- [ ] 配置防火墙规则

### 日常维护：

- [ ] 定期查看错误日志
- [ ] 监控服务器资源使用
- [ ] 更新依赖包版本
- [ ] 定期安全审计

---

## 六、推荐的安全工具

| 工具 | 用途 |
|------|------|
| Cloudflare | CDN + DDoS 防护 |
| 阿里云 WAF | Web 应用防火墙 |
| FastAPI-Limiter | 请求频率限制 |
| OWASP ZAP | 安全扫描工具 |

---

## 七、总结

### 快速实施（优先级）

| 优先级 | 措施 | 预计时间 |
|--------|------|----------|
| 🔴 高 | 关闭调试模式 | 5分钟 |
| 🔴 高 | 添加频率限制 | 30分钟 |
| 🟡 中 | 添加安全响应头 | 15分钟 |
| 🟢 低 | 配置 CDN | 1小时 |

### 成本与收益

| 措施 | 成本 | 收益 |
|------|------|------|
| 代码防护 | 低 | 高 |
| CDN 防护 | 中 | 高 |
| 云 WAF | 高 | 高 |

---

## 八、相关文档

- [SECURITY.md](./SECURITY.md) - 威胁分析
- [DEPLOY.md](./DEPLOY.md) - 部署指南

---

*文档创建时间: 2026-03-12*
