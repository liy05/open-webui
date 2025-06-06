# 企业微信扫码登录配置指南

## 概述

本指南将帮助您在 Open WebUI 中配置企业微信扫码登录功能。该功能使用企业微信官方 `@wecom/jssdk` 实现内嵌登录组件，为用户提供无需跳转的流畅登录体验。

## 特性

- ✅ 企业微信内嵌登录组件（使用官方 @wecom/jssdk）
- ✅ 无需跳转，页面内直接完成登录
- ✅ 自动获取用户信息（姓名、手机号等）
- ✅ 与现有用户系统集成
- ✅ 支持手机号匹配用户账户
- ✅ 管理员界面配置
- ✅ 绿色主题UI设计
- ✅ 响应式设计，支持移动端

## 前置条件

1. **企业微信账号**：需要有企业微信管理员权限
2. **自建应用**：在企业微信管理后台创建自建应用
3. **域名配置**：需要有已备案的域名用于回调
4. **SSL证书**：企业微信要求使用HTTPS协议

## 配置步骤

### 1. 企业微信管理后台配置

#### 1.1 创建自建应用
1. 登录 [企业微信管理后台](https://work.weixin.qq.com/)
2. 进入「应用管理」→「自建」
3. 点击「创建应用」
4. 填写应用信息：
   - 应用名称：Open WebUI
   - 应用介绍：AI聊天平台
   - 应用logo：上传合适的图标

#### 1.2 配置应用权限
1. 在应用详情页面，找到「企业微信授权登录」
2. 设置授权回调域：`yourdomain.com`
3. 在「网页授权及JS-SDK」中配置可信域名：`yourdomain.com`

#### 1.3 获取应用信息
记录以下信息，后续配置需要：
- **企业ID (CorpID)**：在「我的企业」→「企业信息」中查看
- **应用ID (AgentID)**：在应用详情页面查看
- **应用Secret**：在应用详情页面查看（请妥善保管）

### 2. Open WebUI 后端配置

#### 2.1 环境变量配置
在 `.env` 文件中添加：

```bash
# 企业微信配置
WECOM_CORP_ID=ww1234567890abcdef    # 企业ID
WECOM_AGENT_ID=1000001              # 应用ID  
WECOM_SECRET=your_app_secret        # 应用Secret
WECOM_REDIRECT_URI=https://yourdomain.com/auth   # 回调地址
```

#### 2.2 安装依赖
确保已安装必要的Python依赖：

```bash
pip install requests
```

### 3. 前端配置

前端会自动从后端获取企业微信配置，并使用 `@wecom/jssdk` 包实现内嵌登录组件。

## 技术实现

### 登录流程

1. **前端初始化**：页面加载时初始化企业微信 JS-SDK
2. **组件渲染**：使用 `ww.createWWLoginPanel` 创建内嵌登录组件
3. **用户扫码**：用户使用企业微信扫描组件内的二维码
4. **授权确认**：用户在企业微信中确认授权
5. **获取授权码**：JS-SDK 通过 `onLoginSuccess` 回调返回授权码
6. **获取用户信息**：后端使用授权码调用企业微信API获取用户信息
7. **用户匹配**：根据手机号匹配现有用户或创建新用户
8. **登录成功**：返回用户Session，完成登录

### 技术栈

- **前端**：Svelte + 企业微信官方 `@wecom/jssdk`
- **后端**：Python FastAPI + 企业微信API
- **登录组件**：`@wecom/jssdk` 包提供的 `createWWLoginPanel` API

### 核心代码示例

```typescript
// 初始化企业微信登录组件
const initWeComLoginPanel = async () => {
    // 动态导入企业微信 JS-SDK
    const ww = await import('@wecom/jssdk');

    // 创建企业微信登录组件
    wecomLoginPanel = ww.createWWLoginPanel({
        el: '#wecom-login-container',
        params: {
            appid: wecomConfig.corp_id,
            agentid: wecomConfig.agent_id,
            redirect_uri: wecomConfig.redirect_uri,
            state: 'openwebui_auth_' + Math.random().toString(36).substr(2, 9)
        },
        onCheckWeComLogin({ isWeComLogin }) {
            console.log('企业微信环境检测:', isWeComLogin);
        },
        onLoginSuccess({ code }) {
            console.log('企业微信登录成功，获取到code:', code);
            handleWeComLogin(code);
        },
        onLoginFail(error) {
            console.error('企业微信登录失败:', error);
            toast.error('企业微信登录失败，请重试');
        }
    });
};
```

### 文件结构

```
├── backend/
│   ├── open_webui/apps/webui/routers/
│   │   └── auths.py                    # 认证路由，企业微信登录接口
│   └── open_webui/utils/
│       └── wecom_auth.py               # 企业微信API封装
├── src/
│   ├── lib/apis/auths/
│   │   └── index.ts                    # 前端API接口
│   └── routes/auth/
│       └── +page.svelte               # 登录页面组件
├── package.json                       # 包含 @wecom/jssdk 依赖
└── WECOM_LOGIN_GUIDE.md              # 本配置指南
```

## 配置验证

### 1. 检查后端配置
访问：`https://yourdomain.com/api/v1/auths/wecom/config`
应该返回：
```json
{
  "enabled": true,
  "corp_id": "ww1234567890abcdef",
  "agent_id": "1000001",
  "redirect_uri": "https://yourdomain.com/auth"
}
```

### 2. 测试登录流程
1. 访问登录页面
2. 确认显示企业微信内嵌登录组件
3. 使用企业微信扫描组件内的二维码
4. 确认能够成功登录

## 常见问题

### Q1: 企业微信登录组件不显示
**原因**：@wecom/jssdk 加载失败或配置错误
**解决**：
1. 检查网络连接
2. 确认 `@wecom/jssdk` 包已正确安装
3. 查看浏览器控制台错误信息
4. 确认企业微信配置参数正确

### Q2: 提示"JS-SDK加载失败"
**原因**：动态导入失败或包版本不兼容
**解决**：
1. 重新安装 `@wecom/jssdk` 包：`npm install @wecom/jssdk`
2. 确认包版本 >= 1.3.1
3. 检查构建工具配置

### Q3: 扫码后提示"redirect_uri参数错误"
**原因**：回调域名配置不正确
**解决**：
1. 检查企业微信后台的授权回调域配置
2. 确认 `WECOM_REDIRECT_URI` 配置正确
3. 确保使用HTTPS协议

### Q4: 登录成功但无法获取用户信息
**原因**：应用权限不足或API调用失败
**解决**：
1. 检查应用Secret是否正确
2. 确认应用具有获取用户信息的权限
3. 查看后端日志排查API调用问题

### Q5: 手机号匹配失败
**原因**：企业微信中的手机号与系统中的用户手机号不匹配
**解决**：
1. 确保企业微信中员工的手机号准确
2. 系统中用户的手机号与企业微信保持一致
3. 管理员可以在后台手动关联用户

## 安全建议

1. **Secret保护**：企业微信应用Secret需要妥善保管，不要泄露
2. **HTTPS使用**：生产环境必须使用HTTPS协议
3. **域名验证**：确保回调域名配置正确，防止重定向攻击
4. **权限最小化**：应用只申请必要的权限
5. **日志监控**：监控登录日志，及时发现异常访问

## 更新日志

### v1.4.0 (2024-12-19)
- ✨ 使用企业微信官方 @wecom/jssdk 实现内嵌登录组件
- 📝 参考官方文档：https://developer.work.weixin.qq.com/document/path/98268
- 🔧 使用 `ww.createWWLoginPanel` API
- 📱 实现无需跳转的页面内登录体验

### v1.3.0 (2024-12-19)
- 🔄 改回使用企业微信Web登录组件
- 🐛 修复JS-SDK加载失败问题
- 📱 优化移动端显示效果
- 🎨 改进用户界面设计

### v1.2.0 (2024-12-19)
- ✨ 尝试使用企业微信官方JS-SDK (@wecom/jssdk)
- 🐛 发现兼容性问题，需要回退

### v1.1.0 (2024-12-19)
- 🎨 改进UI设计，使用绿色主题
- 📱 优化移动端适配
- 🔧 简化配置流程

### v1.0.0 (2024-12-19)
- 🎉 初始版本发布
- ✨ 企业微信扫码登录功能
- 🔐 用户信息自动获取
- 👥 手机号用户匹配

## 技术支持

如果在配置过程中遇到问题，可以：

1. **查看日志**：检查后端服务日志中的错误信息
2. **控制台调试**：使用浏览器开发者工具查看网络请求和错误
3. **官方文档**：参考[企业微信开发文档](https://developer.work.weixin.qq.com/document/path/98268)
4. **社区支持**：在相关技术社区寻求帮助

---

配置完成后，用户就可以通过企业微信内嵌组件快速登录 Open WebUI 了！🎉 