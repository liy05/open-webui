# 跨域问题解决方案 - CORS Configuration

## 📋 问题描述

跨域资源共享（CORS）问题通常出现在前端应用与后端API不在同一域名下运行时。这个文档提供了全面的解决方案。

## 🎯 解决方案

### 1. 前端 Vite 配置增强

#### 更新 `vite.config.ts`

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import { viteStaticCopy } from 'vite-plugin-static-copy';

export default defineConfig({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',
					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	},
	server: {
		host: '0.0.0.0', // 允许外部访问
		cors: {
			origin: true, // 允许所有来源
			credentials: true, // 允许凭证
			methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
			allowedHeaders: [
				'Content-Type', 
				'Authorization', 
				'X-Requested-With',
				'Accept',
				'Origin',
				'User-Agent',
				'DNT',
				'Cache-Control',
				'X-Mx-ReqToken',
				'Keep-Alive',
				'X-Requested-With',
				'If-Modified-Since'
			]
		},
		allowedHosts: [
			'localhost',
			'127.0.0.1',
			'zhoufy8006.frp.rayfirecloud.com',
			'.frp.rayfirecloud.com',
			'.ngrok.io',
			'.localtunnel.me'
		],
		proxy: {
			// 代理所有 /api 请求到后端服务器
			'/api': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true,
				headers: {
					'Access-Control-Allow-Origin': '*',
					'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, PATCH',
					'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
					'Access-Control-Allow-Credentials': 'true'
				},
				configure: (proxy, _options) => {
					proxy.on('error', (err, _req, _res) => {
						console.log('API proxy error:', err);
					});
					proxy.on('proxyReq', (proxyReq, req, _res) => {
						console.log('Proxying API request:', req.method, req.url);
					});
				}
			},
			// 代理 WebSocket 连接 (Socket.IO) - 精确匹配
			'/ws/socket.io': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true,
				configure: (proxy, _options) => {
					proxy.on('error', (err, _req, _res) => {
						console.log('WebSocket proxy error:', err);
					});
					proxy.on('proxyReq', (proxyReq, req, _res) => {
						console.log('Proxying WebSocket request:', req.method, req.url);
					});
					proxy.on('proxyReqWs', (proxyReq, req, socket) => {
						console.log('Proxying WebSocket upgrade:', req.url);
					});
				}
			},
			// 代理整个 /ws 路径（备用）
			'/ws': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true
			},
			// 代理健康检查
			'/health': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false
			},
			// 代理 Ollama 接口
			'/ollama': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true
			}
		}
	}
});
```

### 2. 后端 CORS 配置优化

#### 检查环境变量

确保设置了正确的 CORS 配置：

```bash
# 开发环境
CORS_ALLOW_ORIGIN="*;http://localhost:5173;http://localhost:8080;http://zhoufy8006.frp.rayfirecloud.com"

# 生产环境（推荐具体域名）
CORS_ALLOW_ORIGIN="https://your-domain.com;https://api.your-domain.com"
```

### 3. 前端请求配置

#### 创建统一的请求工具 `src/lib/utils/api.ts`

```typescript
// 检查当前配置是否已存在此文件
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export const createRequest = (url: string, options: RequestInit = {}) => {
	const fullUrl = API_BASE_URL ? `${API_BASE_URL}${url}` : url;
	
	return fetch(fullUrl, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...options.headers,
		},
		credentials: 'include', // 重要：包含凭证
		mode: 'cors', // 明确指定 CORS 模式
	});
};

export const apiGet = (url: string, options: RequestInit = {}) => {
	return createRequest(url, {
		method: 'GET',
		...options,
	});
};

export const apiPost = (url: string, data?: any, options: RequestInit = {}) => {
	return createRequest(url, {
		method: 'POST',
		body: data ? JSON.stringify(data) : undefined,
		...options,
	});
};
```

### 4. Socket.IO 配置优化

#### 检查 Socket.IO 客户端配置

确保 Socket.IO 客户端正确配置：

```javascript
// 在相关的 Socket.IO 配置文件中
const socket = io({
	path: '/ws/socket.io',
	transports: ['websocket', 'polling'],
	withCredentials: true, // 重要：允许跨域凭证
	cors: {
		origin: true,
		credentials: true
	}
});
```

## 🚀 快速修复步骤

### 步骤 1: 更新 Vite 配置

```bash
# 复制上面的 vite.config.ts 配置
```

### 步骤 2: 重启开发服务器

```bash
npm run dev
```

### 步骤 3: 检查环境变量

```bash
# 在 .env 文件中添加
CORS_ALLOW_ORIGIN="*;http://localhost:5173;http://zhoufy8006.frp.rayfirecloud.com"
```

### 步骤 4: 验证配置

打开浏览器开发者工具，检查：

1. **Network 标签**: 查看请求是否成功
2. **Console 标签**: 查看是否有 CORS 错误
3. **WebSocket 连接**: 确认 Socket.IO 连接正常

## 🔍 故障排除

### 常见 CORS 错误及解决方案

| 错误信息 | 原因 | 解决方案 |
|---------|------|----------|
| `Access to fetch ... has been blocked by CORS policy` | 后端未配置 CORS 或配置错误 | 更新 CORS_ALLOW_ORIGIN 环境变量 |
| `WebSocket connection failed` | WebSocket 代理配置问题 | 检查 vite.config.ts 中的 ws 配置 |
| `Credential is not supported if the CORS header 'Access-Control-Allow-Origin' is '*'` | 通配符与凭证冲突 | 使用具体域名替代 * |
| `Preflight request doesn't pass` | OPTIONS 请求失败 | 确保后端处理 OPTIONS 请求 |

### 调试命令

```bash
# 启动调试模式
npm run debug:websocket

# 检查网络连接
curl -X OPTIONS http://localhost:8080/api/config \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: content-type" \
  -v
```

## 📝 最佳实践

### 1. 开发环境配置

- ✅ 使用代理而不是直接跨域请求
- ✅ 配置详细的错误日志
- ✅ 启用所有必要的 CORS 头

### 2. 生产环境配置

- ✅ 限制 CORS_ALLOW_ORIGIN 到具体域名
- ✅ 启用 HTTPS
- ✅ 配置安全头

### 3. 安全考虑

- ⚠️ 避免在生产环境使用 `*` 通配符
- ⚠️ 限制允许的请求方法和头
- ⚠️ 定期审核 CORS 配置

## 🔗 相关文档

- [MDN CORS 文档](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [Vite 代理配置](https://vitejs.dev/config/server-options.html#server-proxy)
- [FastAPI CORS 中间件](https://fastapi.tiangolo.com/tutorial/cors/)

---

**注意**: 如果问题仍然存在，请提供具体的错误信息和网络请求日志以便进一步诊断。 