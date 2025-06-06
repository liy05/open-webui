# 企业微信认证使用示例

## 环境变量配置示例

```bash
# 基本配置
ENABLE_WECOM_AUTH=true
WECOM_CORP_ID=wwd1234567890abcdef
WECOM_AGENT_ID=1000001
WECOM_SECRET=your_secret_key_here
WECOM_REDIRECT_URI=https://your-domain.com/api/v1/auths/wecom/callback
```

## Docker Compose 配置示例

```yaml
version: '3.8'
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"
    environment:
      - ENABLE_WECOM_AUTH=true
      - WECOM_CORP_ID=wwd1234567890abcdef
      - WECOM_AGENT_ID=1000001
      - WECOM_SECRET=your_secret_key_here
      - WECOM_REDIRECT_URI=https://your-domain.com/api/v1/auths/wecom/callback
    volumes:
      - open-webui:/app/backend/data
    restart: always

volumes:
  open-webui:
```

## API 使用示例

### 1. 获取企业微信配置

```javascript
// GET /api/v1/auths/wecom/config
const config = await fetch('/api/v1/auths/wecom/config', {
    headers: {
        'Authorization': 'Bearer your_token'
    }
});
const data = await config.json();
console.log(data); 
// 输出：
// {
//   "enabled": true,
//   "corp_id": "wwd1234567890abcdef",
//   "agent_id": "1000001",
//   "redirect_uri": "https://your-domain.com/api/v1/auths/wecom/callback"
// }
```

### 2. 重定向到企业微信登录

```javascript
// 直接跳转到企业微信登录页面
window.location.href = '/api/v1/auths/wecom/login';
```

### 3. 使用授权码进行认证

```javascript
// POST /api/v1/auths/wecom/auth
const authResponse = await fetch('/api/v1/auths/wecom/auth', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        code: 'authorization_code_from_wechat'
    })
});

const userData = await authResponse.json();
console.log(userData);
// 输出：
// {
//   "token": "jwt_token",
//   "token_type": "Bearer",
//   "expires_at": 1672531200,
//   "id": "user_id",
//   "email": "user@example.com",
//   "name": "User Name",
//   "role": "user",
//   "profile_image_url": "/user.png",
//   "permissions": {...}
// }
```

## 企业微信应用配置

### 1. 在企业微信管理后台创建应用

1. 登录企业微信管理后台
2. 进入"应用管理" → "自建"
3. 创建新应用，记录 AgentID 和 Secret

### 2. 配置网页授权

1. 在应用详情页面，找到"网页授权及JS-SDK"
2. 设置可信域名：`your-domain.com`
3. 设置网页授权回调域：`your-domain.com`

### 3. 配置应用权限

确保应用有以下权限：
- 通讯录管理权限（读取权限）
- 基础应用权限

## 用户注册要求

### 1. 在 Open WebUI 中注册用户

用户必须先在 Open WebUI 中正常注册账号，并确保：
- 填写正确的手机号码
- 手机号码与企业微信中的手机号一致

### 2. 企业微信用户设置

确保用户在企业微信中：
- 已设置手机号码
- 是企业的正式成员（非外部联系人）

## 常见问题排查

### 1. 配置相关问题

**问题**：登录时提示"企业微信认证未启用"
**解决**：检查 `ENABLE_WECOM_AUTH` 是否设置为 `true`

**问题**：提示"企业微信配置不完整"
**解决**：检查以下配置是否都已设置：
- WECOM_CORP_ID
- WECOM_AGENT_ID
- WECOM_SECRET
- WECOM_REDIRECT_URI

### 2. 授权相关问题

**问题**：授权失败，提示"非法的授权请求"
**解决**：检查回调URL中的 state 参数是否为 "openwebui_auth"

**问题**：提示"只支持企业成员登录"
**解决**：确保登录用户是企业微信的正式成员，不是外部联系人

### 3. 用户匹配问题

**问题**：提示"无法获取用户手机号"
**解决**：
1. 确保应用有获取用户敏感信息的权限
2. 确保用户在企业微信中设置了手机号

**问题**：提示"手机号未在系统中注册"
**解决**：
1. 确保用户已在 Open WebUI 中注册
2. 确保注册时填写的手机号与企业微信中一致

## 安全建议

1. **HTTPS**: 生产环境必须使用 HTTPS
2. **Secret 保护**: 妥善保管企业微信应用的 Secret
3. **域名验证**: 确保回调域名配置正确，避免被恶意利用
4. **权限最小化**: 只给应用必要的权限，避免过度授权

## 测试流程

1. 配置企业微信应用和 Open WebUI
2. 在 Open WebUI 中注册测试用户，设置手机号
3. 在企业微信中确保测试用户有正确的手机号
4. 访问 `/api/v1/auths/wecom/login` 测试登录流程
5. 检查日志确认各步骤是否正常执行 