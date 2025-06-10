# Open WebUI 代理配置指南

## 📋 概述

Open WebUI 支持多种代理配置方式，确保前端能够安全、高效地与后端服务通信。本指南详细说明了开发环境和生产环境的配置方案。

## 🏗️ 架构说明

```
┌─────────────────┐    代理转发    ┌─────────────────┐
│   前端 (5173)   │ ──────────→   │   后端 (8080)   │
│   SvelteKit     │               │    FastAPI      │
└─────────────────┘               └─────────────────┘
```

## 🛠️ 开发环境配置

### 1. Vite 开发代理

`vite.config.ts` 已配置了开发环境代理：

```typescript
server: {
  proxy: {
    // API 请求代理
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      secure: false,
      ws: true, // WebSocket 支持
    },
    // 健康检查代理
    '/health': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      secure: false
    },
    // Ollama 接口代理
    '/ollama': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      secure: false,
      ws: true
    }
  }
}
```

### 2. 启动开发环境

```bash
# 终端 1: 启动后端服务
cd backend
PORT=8080 uvicorn open_webui.main:app --host 0.0.0.0 --reload

# 终端 2: 启动前端开发服务器
npm run dev
# 或指定端口
npm run dev:5050
```

前端服务默认运行在 `http://localhost:5173`，所有 API 请求会自动代理到后端 `http://localhost:8080`。

## 🚀 生产环境配置

### 1. Docker 容器化部署（推荐）

Open WebUI 在生产环境中采用统一服务架构，前端构建文件由后端服务器直接提供：

```yaml
# docker-compose.yaml
services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    ports:
      - "3000:8080"  # 外部端口:容器内端口
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    volumes:
      - open-webui:/app/backend/data
```

**优势**：
- ✅ 无需配置代理
- ✅ 避免 CORS 问题
- ✅ 统一的服务端点
- ✅ 简化部署流程

### 2. Nginx 反向代理配置

如果需要使用 Nginx 作为反向代理：

```nginx
# /etc/nginx/sites-available/open-webui
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        try_files $uri $uri/ @backend;
    }

    # API 请求代理
    location /api/ {
        proxy_pass http://localhost:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Ollama 接口代理
    location /ollama/ {
        proxy_pass http://localhost:8080/ollama/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 健康检查
    location /health {
        proxy_pass http://localhost:8080/health;
        proxy_set_header Host $host;
    }

    # 后端服务（备用）
    location @backend {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Apache 反向代理配置

```apache
# /etc/apache2/sites-available/open-webui.conf
<VirtualHost *:80>
    ServerName your-domain.com
    
    # 启用代理模块
    ProxyPreserveHost On
    ProxyRequests Off
    
    # API 请求代理
    ProxyPass /api/ http://localhost:8080/api/
    ProxyPassReverse /api/ http://localhost:8080/api/
    
    # Ollama 接口代理
    ProxyPass /ollama/ http://localhost:8080/ollama/
    ProxyPassReverse /ollama/ http://localhost:8080/ollama/
    
    # 健康检查
    ProxyPass /health http://localhost:8080/health
    ProxyPassReverse /health http://localhost:8080/health
    
    # WebSocket 支持
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule ^/?(.*) "ws://localhost:8080/$1" [P,L]
    
    # 其他请求代理到后端
    ProxyPass / http://localhost:8080/
    ProxyPassReverse / http://localhost:8080/
</VirtualHost>
```

## 🔧 环境变量配置

### 开发环境

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:5173
BACKEND_PORT=8080
```

### 生产环境

```bash
# .env.production
PORT=8080
HOST=0.0.0.0
CORS_ALLOW_ORIGIN=http://localhost:5173;http://localhost:8080;*
```

## 🔍 故障排除

### 1. CORS 错误

**问题**: 开发环境出现跨域请求错误
**解决**: 确保后端配置正确的 CORS 设置

```python
# backend/open_webui/config.py
CORS_ALLOW_ORIGIN = [
    "*",
    "http://localhost:5173",
    "http://localhost:8080"
]
```

### 2. 代理连接失败

**问题**: 前端无法连接到后端服务
**检查清单**:
- ✅ 后端服务是否运行在 8080 端口
- ✅ `vite.config.ts` 代理配置是否正确
- ✅ 防火墙是否阻止了连接

### 3. WebSocket 连接问题

**问题**: 实时功能无法正常工作
**解决**: 确保代理配置支持 WebSocket

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8080',
    ws: true, // 启用 WebSocket 支持
    changeOrigin: true
  }
}
```

## 📊 性能优化

### 1. 开发环境

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8080',
      changeOrigin: true,
      timeout: 30000, // 30秒超时
      proxyTimeout: 30000
    }
  }
}
```

### 2. 生产环境

```nginx
# Nginx 配置优化
location /api/ {
    proxy_pass http://localhost:8080/api/;
    proxy_buffering on;
    proxy_buffer_size 8k;
    proxy_buffers 16 8k;
    proxy_connect_timeout 30s;
    proxy_send_timeout 30s;
    proxy_read_timeout 30s;
}
```

## 🔐 安全配置

### 1. 生产环境安全设置

```nginx
# 安全头设置
add_header X-Frame-Options SAMEORIGIN;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### 2. 限制访问

```nginx
# 限制 API 访问
location /api/ {
    # 限制请求频率
    limit_req zone=api burst=20 nodelay;
    
    # 只允许特定方法
    limit_except GET POST PUT DELETE {
        deny all;
    }
    
    proxy_pass http://localhost:8080/api/;
}
```

## 📝 总结

1. **开发环境**: 使用 Vite 内置代理，配置简单，自动处理 CORS
2. **生产环境**: 推荐使用 Docker 统一服务架构，简化部署
3. **反向代理**: 如需独立部署，可使用 Nginx/Apache 反向代理
4. **安全性**: 生产环境需要配置适当的安全策略和访问控制

通过以上配置，你可以确保前端与后端的安全、高效通信，同时保持良好的开发体验。 