# Open WebUI 远程访问和内网穿透配置指南

## 🌐 概述

当你需要通过内网穿透工具（如 frp、ngrok）或远程网络访问 Open WebUI 开发环境时，需要进行相应的安全配置。本指南详细说明了各种远程访问场景的配置方法。

## 🔧 Vite 开发服务器配置

### 1. 允许特定主机访问

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    host: '0.0.0.0', // 监听所有网络接口
    port: 5173,      // 开发服务器端口
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'your-domain.frp.rayfirecloud.com', // 你的 frp 域名
      '.frp.rayfirecloud.com',            // 允许所有 frp 子域名
      '.ngrok.io',                        // 允许 ngrok 域名
      '.localtunnel.me'                   // 允许 localtunnel 域名
    ],
    // ... 其他配置
  }
});
```

### 2. 完整的安全配置

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: [
      // 本地访问
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      
      // 内网 IP 范围
      /^192\.168\.\d+\.\d+$/,
      /^10\.\d+\.\d+\.\d+$/,
      /^172\.(1[6-9]|2\d|3[01])\.\d+\.\d+$/,
      
      // 内网穿透服务
      '.frp.rayfirecloud.com',
      '.ngrok.io',
      '.localtunnel.me',
      '.serveo.net',
      
      // 自定义域名（根据需要添加）
      'your-custom-domain.com'
    ],
    // CORS 配置
    cors: {
      origin: true,
      credentials: true
    }
  }
});
```

## 🛠️ 常见内网穿透工具配置

### 1. FRP (Fast Reverse Proxy)

#### 客户端配置 (frpc.ini)

```ini
[common]
server_addr = frp.rayfirecloud.com
server_port = 7000
token = your_token

[open-webui-dev]
type = http
local_ip = 127.0.0.1
local_port = 5173
custom_domains = zhoufy8006.frp.rayfirecloud.com

[open-webui-api]
type = http
local_ip = 127.0.0.1
local_port = 8080
custom_domains = api.zhoufy8006.frp.rayfirecloud.com
```

#### 启动命令

```bash
# 启动 frp 客户端
./frpc -c frpc.ini

# 启动前端开发服务器
npm run dev

# 启动后端服务器
cd backend && python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080
```

### 2. Ngrok

```bash
# 安装 ngrok
npm install -g ngrok

# 启动前端隧道
ngrok http 5173 --host-header="localhost:5173"

# 启动后端隧道
ngrok http 8080 --host-header="localhost:8080"
```

#### Vite 配置

```typescript
server: {
  allowedHosts: [
    'localhost',
    /\.ngrok\.io$/,
    /\.ngrok-free\.app$/
  ]
}
```

### 3. LocalTunnel

```bash
# 安装 localtunnel
npm install -g localtunnel

# 启动前端隧道
lt --port 5173 --subdomain your-frontend

# 启动后端隧道
lt --port 8080 --subdomain your-backend
```

## 🔐 安全考虑

### 1. 开发环境安全设置

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    // 仅在开发环境允许外部访问
    host: process.env.NODE_ENV === 'development' ? '0.0.0.0' : 'localhost',
    
    // 基于环境变量的主机允许列表
    allowedHosts: process.env.ALLOWED_HOSTS 
      ? process.env.ALLOWED_HOSTS.split(',')
      : ['localhost', '127.0.0.1'],
      
    // 开发环境 HTTPS（可选）
    https: process.env.HTTPS === 'true' ? {
      key: fs.readFileSync('path/to/key.pem'),
      cert: fs.readFileSync('path/to/cert.pem')
    } : false
  }
});
```

### 2. 环境变量配置

```bash
# .env.development
NODE_ENV=development
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.frp.rayfirecloud.com
HTTPS=false

# .env.local (不提交到 git)
FRP_DOMAIN=your-subdomain.frp.rayfirecloud.com
API_BASE_URL=https://api.your-subdomain.frp.rayfirecloud.com
```

### 3. 后端 CORS 配置

```python
# backend/open_webui/config.py
CORS_ALLOW_ORIGIN = os.environ.get(
    "CORS_ALLOW_ORIGIN", 
    "*;http://localhost:5173;https://your-domain.frp.rayfirecloud.com"
).split(";")
```

## 🚀 启动脚本示例

### 1. 开发环境启动脚本

```bash
#!/bin/bash
# start-dev.sh

echo "启动 Open WebUI 开发环境..."

# 检查是否需要启动 frp
if [ "$USE_FRP" = "true" ]; then
    echo "启动 FRP 客户端..."
    ./frpc -c frpc.ini &
    FRP_PID=$!
    echo "FRP PID: $FRP_PID"
fi

# 启动后端服务器
echo "启动后端服务器..."
cd backend
PORT=8080 uvicorn open_webui.main:app --host 0.0.0.0 --reload &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 等待后端启动
sleep 3

# 启动前端开发服务器
echo "启动前端开发服务器..."
cd ..
npm run dev &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

# 创建停止脚本
cat > stop-dev.sh << EOF
#!/bin/bash
echo "停止开发服务器..."
kill $FRONTEND_PID $BACKEND_PID
if [ "$USE_FRP" = "true" ]; then
    kill $FRP_PID
fi
echo "所有服务已停止"
EOF

chmod +x stop-dev.sh

echo "开发环境启动完成！"
echo "前端访问: http://localhost:5173"
if [ "$USE_FRP" = "true" ]; then
    echo "远程访问: https://$FRP_DOMAIN"
fi
echo "运行 ./stop-dev.sh 停止所有服务"

# 等待用户中断
wait
```

### 2. Package.json 脚本

```json
{
  "scripts": {
    "dev": "vite dev --host 0.0.0.0",
    "dev:tunnel": "ALLOWED_HOSTS=localhost,.ngrok.io npm run dev",
    "dev:frp": "USE_FRP=true ./start-dev.sh",
    "dev:secure": "HTTPS=true npm run dev"
  }
}
```

## 🔍 故障排除

### 1. 主机不被允许错误

**错误信息**: `This host is not allowed`

**解决方案**:
```typescript
// 添加到 vite.config.ts
server: {
  allowedHosts: [
    'your-domain.com', // 添加你的域名
    '.your-service.com' // 或使用通配符
  ]
}
```

### 2. CORS 错误

**错误信息**: `Access to fetch at 'http://localhost:8080/api' from origin 'https://your-domain.com' has been blocked by CORS policy`

**解决方案**:
```python
# backend/open_webui/config.py
CORS_ALLOW_ORIGIN = [
    "https://your-domain.com",
    "http://localhost:5173"
]
```

### 3. WebSocket 连接失败

**错误信息**: `WebSocket connection failed` 或 `SvelteKitError: Not found: /ws/socket.io/`

**解决方案**:
```typescript
// vite.config.ts
server: {
  proxy: {
    // API 代理
    '/api': {
      target: 'http://localhost:8080',
      ws: true, // 确保启用 WebSocket
      changeOrigin: true
    },
    // WebSocket 代理
    '/ws': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      secure: false,
      ws: true,
      configure: (proxy, _options) => {
        proxy.on('error', (err, _req, _res) => {
          console.log('WebSocket proxy error:', err);
        });
      }
    },
    // Socket.IO 代理
    '/socket.io': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      secure: false,
      ws: true
    }
  }
}
```

**常见 Socket.IO 问题**:

1. **路径不匹配**: 确保前端和后端使用相同的 Socket.IO 路径
2. **传输协议**: Socket.IO 会尝试 WebSocket，失败时回退到轮询
3. **跨域问题**: 确保 CORS 配置允许 Socket.IO 连接

**调试方法**:
```bash
# 1. 使用内置调试工具
npm run debug:websocket

# 2. 手动检查端点
# 检查后端 Socket.IO 服务是否运行
curl http://localhost:8080/ws/socket.io/

# 检查代理是否正常工作
curl http://localhost:5173/ws/socket.io/

# 检查健康状态
curl http://localhost:8080/health
curl http://localhost:5173/health

# 3. 浏览器调试
# 在浏览器开发者工具中检查:
# - Network 选项卡中的 WebSocket 连接
# - Console 中的 Socket.IO 连接日志
# - Application 选项卡中的 WebSocket 消息
```

**常见错误和解决方案**:

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `Not found: /ws/socket.io/` | Vite 代理配置错误 | 确保 `/ws/socket.io` 路径被正确代理 |
| `Connection timeout` | 后端服务未启动 | 启动后端服务器并确保监听 8080 端口 |
| `CORS error` | 跨域配置问题 | 更新后端 CORS 设置 |
| `WebSocket upgrade failed` | 代理不支持 WebSocket | 在代理配置中启用 `ws: true` |

### 4. 内网穿透服务连接问题

**检查清单**:
- ✅ frp/ngrok 客户端是否正常运行
- ✅ 本地服务器是否监听 0.0.0.0
- ✅ 防火墙是否阻止了端口
- ✅ 域名解析是否正确

## 📋 配置检查清单

在使用远程访问前，请确认以下配置：

### 前端配置
- [ ] `vite.config.ts` 中添加了正确的 `allowedHosts`
- [ ] 开发服务器监听 `0.0.0.0`
- [ ] 代理配置指向正确的后端地址

### 后端配置
- [ ] 后端服务器监听 `0.0.0.0:8080`
- [ ] CORS 配置包含前端域名
- [ ] 防火墙允许 8080 端口访问

### 内网穿透配置
- [ ] 隧道配置正确（域名、端口）
- [ ] 隧道服务正常运行
- [ ] DNS 解析正确

### 安全配置
- [ ] 仅在开发环境启用外部访问
- [ ] 生产环境禁用开发模式
- [ ] 敏感信息使用环境变量

通过以上配置，你就可以安全地通过内网穿透工具访问 Open WebUI 开发环境了！ 