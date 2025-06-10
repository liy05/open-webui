import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

// /** @type {import('vite').Plugin} */
// const viteServerConfig = {
// 	name: 'log-request-middleware',
// 	configureServer(server) {
// 		server.middlewares.use((req, res, next) => {
// 			res.setHeader('Access-Control-Allow-Origin', '*');
// 			res.setHeader('Access-Control-Allow-Methods', 'GET');
// 			res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
// 			res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
// 			next();
// 		});
// 	}
// };

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
			'zhoufy8006.frp.rayfirecloud.com', // 允许 frp 域名访问
			'.frp.rayfirecloud.com', // 允许所有 frp 子域名
			'.ngrok.io', // 支持 ngrok
			'.localtunnel.me' // 支持 localtunnel
		],
		proxy: {
			// 代理所有 /api 请求到后端服务器
			'/api': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true, // 支持 WebSocket
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
			// 代理 WebSocket 连接 (Socket.IO) - 主要路径
			'/ws/socket.io': {
				target: 'http://localhost:8080',
				changeOrigin: true,
				secure: false,
				ws: true, // 启用 WebSocket 支持
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
