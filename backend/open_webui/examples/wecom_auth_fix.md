# 企业微信认证获取用户敏感信息修复说明

## 问题描述

在企业微信OAuth认证过程中，出现以下错误：

```
2025-06-06 20:20:55.460 | ERROR | open_webui.routers.wecom_auth:get_user_sensitive_info:158 - 获取用户敏感信息失败: {'errcode': 40058, 'errmsg': 'missing field `user_ticket`. invalid Request Parameter'}
```

## 问题原因

### 1. 错误的API端点
- **原来使用**: `https://qyapi.weixin.qq.com/cgi-bin/user/getuserdetail`
- **应该使用**: `https://qyapi.weixin.qq.com/cgi-bin/auth/getuserdetail`

### 2. 错误的参数格式
- **原来使用**: GET请求，传递`userid`参数
- **应该使用**: POST请求，传递`user_ticket`参数

### 3. 授权范围不足
- **原来使用**: `snsapi_base` (只能获取基础信息)
- **应该使用**: `snsapi_privateinfo` (可以获取敏感信息)

### 4. 自动登录问题
- **问题**: 企业微信认证成功后仍然跳转到登录页面
- **原因**: 前端只检查`localStorage.token`，但企业微信认证设置的是Cookie

## 修复内容

### 1. 修改API方法签名和实现

```python
# 修复前
def get_user_sensitive_info(self, userid: str) -> dict:
    url = "https://qyapi.weixin.qq.com/cgi-bin/user/getuserdetail"
    params = {
        "access_token": access_token,
        "userid": userid
    }
    response = requests.get(url, params=params, timeout=10)

# 修复后  
def get_user_sensitive_info(self, user_ticket: str) -> dict:
    url = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserdetail"
    data = {
        "user_ticket": user_ticket
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(
        f"{url}?access_token={access_token}",
        json=data,
        headers=headers,
        timeout=10
    )
```

### 2. 修改OAuth授权范围

```python
# 修复前
params = {
    "scope": "snsapi_base",
}

# 修复后
params = {
    "scope": "snsapi_privateinfo",  # 使用 snsapi_privateinfo 来获取敏感信息
}
```

### 3. 修改回调处理逻辑

```python
# 修复前
user_info = wecom_api.get_user_info(code)
userid = user_info.get("userid")
user_sensitive = wecom_api.get_user_sensitive_info(userid)

# 修复后
user_info = wecom_api.get_user_info(code)
userid = user_info.get("userid")
user_ticket = user_info.get("user_ticket")  # 获取user_ticket

if user_ticket:
    user_sensitive = wecom_api.get_user_sensitive_info(user_ticket)
```

### 4. 修复自动登录问题

```python
# 修复前 - 只重定向
return RedirectResponse(url="/", status_code=302)

# 修复后 - 使用专门的成功页面
redirect_url = f"/api/v1/auths/wecom/success?token={token}"
return RedirectResponse(url=redirect_url, status_code=302)

# 添加成功页面端点
@router.get("/success")
async def wecom_success(request: Request, token: str):
    # 验证token有效性
    data = decode_token(token)
    if not data or "id" not in data:
        raise HTTPException(status_code=400, detail="无效的token")
    
    # 返回HTML页面设置localStorage
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>登录成功 - Open WebUI</title>
        <script>
            var token = {json.dumps(token)};
            localStorage.setItem('token', token);
            setTimeout(function() {{
                window.location.href = '/';
            }}, 100);
        </script>
    </head>
    <body>
        <h2>🎉 企业微信登录成功</h2>
        <p>正在跳转到主页...</p>
    </body>
    </html>
    '''
    return HTMLResponse(content=html_content)
```

## 企业微信应用配置要求

### 1. 敏感信息权限配置
在企业微信管理后台的应用详情中，需要：
- 勾选"手机号"等敏感字段
- 确保应用有访问成员敏感信息的权限

### 2. 可信域名配置
确保回调域名已正确配置在可信域名列表中。

### 3. 网页授权回调域
设置正确的回调URL：`your_domain/api/v1/auths/wecom/callback`

## 用户体验变化

### 修复前
- 用户可能看到静默授权，但获取敏感信息失败
- 错误信息不够明确
- 认证成功后仍然跳转到登录页面

### 修复后  
- 用户首次登录时会看到授权确认页面
- 需要用户手动确认授权访问敏感信息
- 提供更清晰的错误提示
- 认证成功后自动登录并跳转到主页

## API调用流程

1. **构造授权链接** (scope=snsapi_privateinfo)
2. **用户授权确认** (选择是否共享敏感信息)
3. **获取授权码** (包含user_ticket)
4. **获取用户基本信息** (通过code)
5. **获取用户敏感信息** (通过user_ticket)
6. **匹配系统用户** (通过手机号)
7. **完成登录** (设置Cookie和localStorage)
8. **自动跳转** (返回HTML页面实现无缝跳转)

## 自动登录机制说明

### 问题分析
- **后端**: 支持从Cookie或Authorization Header读取token
- **前端**: 只检查`localStorage.token`
- **企业微信认证**: 只设置了httpOnly Cookie

### 解决方案
1. **设置Cookie**: 用于后端API认证
2. **设置localStorage**: 用于前端状态检查
3. **HTML页面**: 通过JavaScript桥接Cookie和localStorage

### 安全考虑
- Cookie设置为httpOnly，防止XSS攻击
- localStorage用于前端状态，不涉及敏感操作
- token具有过期时间限制

## 错误处理改进

```python
# 增加了更详细的错误处理
if not phone_number:
    raise HTTPException(
        status_code=400,
        detail="无法获取用户手机号，请确保在企业微信中设置了手机号，或者在应用中启用敏感信息授权"
    )
```

## 向后兼容性

- 保持了原有的API接口不变
- 如果无法获取敏感信息，会尝试从基本信息中获取手机号
- 错误提示更加友好和具体
- 支持Cookie和localStorage双重认证机制

## 测试建议

1. 测试首次登录的授权流程
2. 测试敏感信息授权确认
3. 测试手机号匹配逻辑
4. 测试错误场景的提示信息
5. **新增**: 测试自动登录跳转功能
6. **新增**: 测试localStorage和Cookie的同步设置 