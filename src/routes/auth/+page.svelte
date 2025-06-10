<script lang="ts">
	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import {
		ldapUserSignIn,
		getSessionUser,
		userSignIn,
		userSignUp,
		sendSmsCode,
		phoneSignIn,
		getWeComConfig,
		weComAuth
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	
	// 静态导入企业微信 JS-SDK
	import * as ww from '@wecom/jssdk';

	const i18n = getContext('i18n');

	let loaded = false;

	// 企业微信配置
	let wecomConfig = {
		enabled: false,
		corp_id: '',
		agent_id: '',
		redirect_uri: ''
	};

	// 企业微信登录组件相关变量
	let wecomLoginPanel = null;
	let wecomInitialized = false;

	// 响应模式变化，在切换到企业微信时自动初始化
	$: if (mode === 'wecom' && !wecomInitialized && wecomConfig.enabled) {
		setTimeout(() => {
			const container = document.getElementById('wecom-login-container');
			if (container) {
				console.log('响应式初始化企业微信登录组件');
				initWeComLoginPanel();
			}
		}, 100);
	}

	let mode = 'phone'; // 默认使用手机号登录

	let name = '';
	let email = '';
	let password = '';
	let phoneNumber = '';
	let verificationCode = '';
	let countDown = 0;
	let intervalId: NodeJS.Timeout | null = null;

	let ldapUsername = '';

	const querystringValue = (key) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`您已成功登录。`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const phoneSignInHandler = async () => {
		const sessionUser = await phoneSignIn(phoneNumber, verificationCode).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	// 初始化企业微信登录组件
	const initWeComLoginPanel = async () => {
		if (!wecomConfig.enabled || !wecomConfig.corp_id || !wecomConfig.agent_id) {
			console.error('企业微信配置不完整');
			return;
		}

		if (wecomInitialized) {
			console.log('企业微信登录组件已初始化，跳过重复初始化');
			return;
		}

		try {
			// 检查容器是否存在
			const container = document.getElementById('wecom-login-container');
			if (!container) {
				console.error('企业微信登录容器不存在');
				return;
			}

			// 清空容器并重置
			container.innerHTML = '';
			
			// 如果之前有登录面板，先销毁
			if (wecomLoginPanel && wecomLoginPanel.destroy) {
				try {
					wecomLoginPanel.destroy();
				} catch (e) {
					console.log('销毁旧的登录面板时出错:', e);
				}
				wecomLoginPanel = null;
			}

			// 使用静态导入的 ww 模块
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

			wecomInitialized = true;
			console.log('企业微信登录组件初始化成功');
			
		} catch (error) {
			console.error('企业微信 JS-SDK 初始化失败:', error);
			toast.error('企业微信登录组件加载失败');
		}
	};

	// 处理企业微信登录
	const handleWeComLogin = async (authCode: string) => {
		try {
			const sessionUser = await weComAuth(authCode);
			if (sessionUser) {
				await setSessionUser(sessionUser);
			} else {
				toast.error('企业微信登录失败，请重试');
			}
		} catch (error) {
			console.error('企业微信登录处理失败:', error);
			toast.error(`企业微信登录失败: ${error}`);
		}
	};

	// 企业微信登录处理（保留用于兼容性）
	const wecomSignInHandler = async () => {
		// 现在使用JS-SDK组件，不需要额外处理
		if (!wecomInitialized) {
			await initWeComLoginPanel();
		}
	};

	const sendSmsCodeHandler = async () => {
		if (countDown > 0) return;

		if (!phoneNumber || phoneNumber.length !== 11 || !/^\d+$/.test(phoneNumber)) {
			toast.error($i18n.t('请输入有效的手机号码'));
			return;
		}

		let success = false;
		
		try {
			const result = await sendSmsCode(phoneNumber);
			console.log('SMS send result:', result);
			
			// 验证返回结果
			if (result && result.message && result.message === "验证码发送成功") {
				success = true;
			} else {
				console.error('Unexpected result:', result);
				toast.error($i18n.t('验证码发送失败，请稍后重试'));
			}
		} catch (error) {
			console.error('SMS send error:', error);
			toast.error(`${error}`);
		}

		// 只有明确成功时才显示成功消息和启动倒计时
		if (success) {
			// 设置计时器，60秒内不允许重复发送
			countDown = 60;
			intervalId = setInterval(() => {
				countDown--;
				if (countDown <= 0 && intervalId) {
					clearInterval(intervalId);
					intervalId = null;
				}
			}, 1000);

			toast.success($i18n.t('验证码已发送'));
		}
	};

	const submitHandler = async () => {
		if (mode === 'wecom') {
			await wecomSignInHandler();
		} else if (mode === 'phone') {
			await phoneSignInHandler();
		} else if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) {
			return;
		}
		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	// 检查企业微信回调（保留用于兼容其他登录方式）
	const checkWeComCallback = async () => {
		const code = querystringValue('code');
		const state = querystringValue('state');
		
		if (code && state && (state === 'openwebui_auth' || state.startsWith('openwebui_auth_'))) {
			try {
				// 清理URL参数，避免重复处理
				const url = new URL(window.location.href);
				url.searchParams.delete('code');
				url.searchParams.delete('state');
				window.history.replaceState({}, document.title, url.toString());

				await handleWeComLogin(code);
			} catch (error) {
				console.error('WeChat Enterprise login error:', error);
				toast.error(`企业微信登录失败: ${error}`);
			}
		}
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo') as HTMLImageElement;

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				logo.src = '/static/logo-dark.svg';
			} else {
				logo.src = '/static/logo.svg';
			}
		}
	}

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		
		// 获取企业微信配置
		try {
			const config = await getWeComConfig();
			if (config) {
				wecomConfig = config;
				// 暂时屏蔽PC端扫码登录，默认使用手机号登录
				// if (wecomConfig.enabled && wecomConfig.corp_id && wecomConfig.agent_id) {
				// 	mode = 'wecom';
				// 	// 等待DOM更新后初始化企业微信登录组件
				// 	setTimeout(initWeComLoginPanel, 100);
				// }
			}
		} catch (error) {
			console.error('Failed to get WeChat Enterprise config:', error);
		}

		await checkOauthCallback();
		await checkWeComCallback();

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 dark:from-gray-950 dark:via-blue-950 dark:to-indigo-950 relative overflow-hidden">
	<!-- 背景装饰 -->
	<div class="absolute inset-0 bg-grid-pattern opacity-5"></div>
	<div class="absolute top-0 left-0 w-full h-full">
		<div class="absolute top-[-50%] right-[-20%] w-96 h-96 bg-blue-400/20 rounded-full blur-3xl animate-pulse"></div>
		<div class="absolute bottom-[-50%] left-[-20%] w-96 h-96 bg-purple-400/20 rounded-full blur-3xl animate-pulse"></div>
	</div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-50" />

	{#if loaded}
		<!-- 头部Logo -->
		<div class="absolute top-8 left-8 z-50">
			<div class="flex items-center space-x-3">
				<img
					id="logo"
					crossorigin="anonymous"
					src="/static/logo.svg"
					class="w-10 h-10 drop-shadow-sm"
					alt="Logo"
				/>
				<span class="text-lg font-bold text-gray-900 dark:text-white">{$WEBUI_NAME}</span>
			</div>
		</div>

		<div class="min-h-screen flex items-center justify-center p-4 relative z-10">
			<div class="w-full max-w-md">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<!-- 加载状态 -->
					<div class="bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 dark:border-gray-800/50 p-8">
						<div class="text-center">
							<div class="w-16 h-16 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full flex items-center justify-center mx-auto mb-4 animate-pulse">
								<svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
									<path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2Z"/>
								</svg>
							</div>
							<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">正在登录</h2>
							<p class="text-gray-600 dark:text-gray-400">请稍候片刻...</p>
						</div>
					</div>
				{:else}
					<!-- 主登录卡片 -->
					<div class="bg-white/90 dark:bg-gray-900/90 backdrop-blur-xl rounded-2xl shadow-xl border border-white/20 dark:border-gray-800/50 overflow-hidden">
						<!-- 顶部装饰条 -->
						<div class="h-1 bg-gradient-to-r from-blue-500 via-purple-500 to-indigo-500"></div>
						
						<div class="p-6">
							<!-- 标题区域 -->
							<div class="text-center mb-6">
								<h1 class="text-xl font-bold text-gray-900 dark:text-white">
									{#if mode === 'wecom'}
										企业微信登录
									{:else if mode === 'phone'}
										手机号登录
									{:else if mode === 'signup'}
										创建账户
									{:else}
										登录
									{/if}
								</h1>
							</div>

							<!-- 表单内容 -->
							<form on:submit={(e) => { e.preventDefault(); submitHandler(); }}>
								{#if mode === 'wecom'}
									<!-- 企业微信登录 -->
									<div class="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4">
										<div id="wecom-login-container" class="min-h-[180px] flex items-center justify-center">
											{#if !wecomInitialized}
												<div class="w-6 h-6 border-2 border-green-500 border-t-transparent rounded-full animate-spin"></div>
											{/if}
										</div>
									</div>
								{:else}
									<!-- 常规登录表单 -->
									<div class="space-y-4">
										{#if mode === 'signup'}
											<div>
												<label for="name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">姓名</label>
												<input
													bind:value={name}
													type="text"
													id="name"
													class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
													placeholder="请输入您的姓名"
													required
												/>
											</div>
										{/if}

										{#if mode === 'phone'}
											<div>
												<label for="phone" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">手机号码</label>
												<input
													bind:value={phoneNumber}
													type="tel"
													id="phone"
													class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
													placeholder="请输入手机号码"
													required
												/>
											</div>
											<div>
												<label for="code" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">验证码</label>
												<div class="flex space-x-3">
													<input
														bind:value={verificationCode}
														type="text"
														id="code"
														class="flex-1 px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
														placeholder="验证码"
														required
													/>
													<button
														type="button"
														on:click={sendSmsCodeHandler}
														disabled={countDown > 0}
														class="px-4 py-3 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 border border-gray-200 dark:border-gray-600 rounded-xl transition-colors text-sm disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
													>
														{countDown > 0 ? `${countDown}s` : '获取验证码'}
													</button>
												</div>
											</div>
										{:else if mode === 'ldap'}
											<div>
												<label for="username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">用户名</label>
												<input
													bind:value={ldapUsername}
													type="text"
													id="username"
													class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
													placeholder="请输入用户名"
													required
												/>
											</div>
										{:else}
											<div>
												<label for="email" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">邮箱</label>
												<input
													bind:value={email}
													type="email"
													id="email"
													class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
													placeholder="请输入邮箱地址"
													required
												/>
											</div>
										{/if}

										{#if mode !== 'phone'}
											<div>
												<label for="password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">密码</label>
												<input
													bind:value={password}
													type="password"
													id="password"
													class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all outline-none"
													placeholder="请输入密码"
													required
												/>
											</div>
										{/if}

										{#if mode !== 'wecom'}
											<button
												type="submit"
												class="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium py-3 rounded-xl transition-all duration-200 transform hover:scale-[1.02] shadow-lg shadow-blue-500/25"
											>
												{#if mode === 'signup'}
													创建账户
												{:else if mode === 'phone'}
													验证并登录
												{:else if mode === 'ldap'}
													LDAP 登录
												{:else}
													登录
												{/if}
											</button>
										{/if}

										{#if mode === 'signin' && $config?.features.enable_signup}
											<div class="text-center">
												<span class="text-sm text-gray-600 dark:text-gray-400">还没有账户？</span>
												<button
													type="button"
													on:click={() => mode = 'signup'}
													class="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium ml-1"
												>
													立即注册
												</button>
											</div>
										{:else if mode === 'signup'}
											<div class="text-center">
												<span class="text-sm text-gray-600 dark:text-gray-400">已有账户？</span>
												<button
													type="button"
													on:click={() => mode = 'signin'}
													class="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 font-medium ml-1"
												>
													立即登录
												</button>
											</div>
										{/if}
									</div>
								{/if}
							</form>
						</div>

						<!-- 底部登录方式切换 -->
						<div class="bg-gray-50/50 dark:bg-gray-800/50 px-6 py-4 border-t border-gray-100 dark:border-gray-800">
							<!-- 登录方式切换按钮 -->
							<div class="flex flex-wrap gap-2 justify-center">
									<!-- 企业微信登录 - 暂时屏蔽PC端扫码登录 -->
									{#if false && wecomConfig?.enabled}
										<button
											type="button"
											on:click={() => {
												if (mode === 'wecom') {
													mode = 'signin';
												} else {
													mode = 'wecom';
													// 重置初始化状态，确保可以重新初始化
													wecomInitialized = false;
													// 使用更长的延迟确保DOM更新完成
													setTimeout(() => {
														console.log('切换到企业微信登录模式，开始初始化');
														initWeComLoginPanel();
													}, 200);
												}
											}}
											class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm border {mode === 'wecom' ? 'bg-green-100 text-green-700 border-green-300 dark:bg-green-900/30 dark:text-green-400 dark:border-green-700' : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 dark:border-gray-600'}"
										>
											<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12,2C6.48,2,2,6.48,2,12s4.48,10,10,10s10-4.48,10-10S17.52,2,12,2z"/>
											</svg>
											<span>企业微信</span>
										</button>
									{/if}

									<!-- 手机号登录 - 始终显示 -->
									<button
										type="button"
										on:click={() => mode = mode === 'phone' ? 'signin' : 'phone'}
										class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm border {mode === 'phone' ? 'bg-blue-100 text-blue-700 border-blue-300 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-700' : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 dark:border-gray-600'}"
									>
										<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
											<path d="M6.62,10.79C8.06,13.62 10.38,15.94 13.21,17.38L15.41,15.18C15.69,14.9 16.08,14.82 16.43,14.93C17.55,15.3 18.75,15.5 20,15.5A1,1 0 0,1 21,16.5V20A1,1 0 0,1 20,21A17,17 0 0,1 3,4A1,1 0 0,1 4,3H7.5A1,1 0 0,1 8.5,4C8.5,5.25 8.7,6.45 9.07,7.57C9.18,7.92 9.1,8.31 8.82,8.59L6.62,10.79Z"/>
										</svg>
										<span>手机号</span>
									</button>

									<!-- 邮箱登录 - 始终显示 -->
									<button
										type="button"
										on:click={() => mode = mode === 'signin' || mode === 'signup' ? 'phone' : 'signin'}
										class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm border {mode === 'signin' || mode === 'signup' ? 'bg-purple-100 text-purple-700 border-purple-300 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-700' : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 dark:border-gray-600'}"
									>
										<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
											<path d="M20,8L12,13L4,8V6L12,11L20,6M20,4H4C2.89,4 2,4.89 2,6V18A2,2 0 0,0 4,20H20A2,2 0 0,0 22,18V6C22,4.89 21.1,4 20,4Z"/>
										</svg>
										<span>邮箱</span>
									</button>

									<!-- LDAP登录 -->
									{#if $config?.features.enable_ldap}
										<button
											type="button"
											on:click={() => mode = mode === 'ldap' ? 'signin' : 'ldap'}
											class="flex items-center space-x-2 px-3 py-2 rounded-lg transition-all text-sm border {mode === 'ldap' ? 'bg-indigo-100 text-indigo-700 border-indigo-300 dark:bg-indigo-900/30 dark:text-indigo-400 dark:border-indigo-700' : 'bg-white hover:bg-gray-50 text-gray-700 border-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300 dark:border-gray-600'}"
										>
											<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
												<path d="M12,4A4,4 0 0,1 16,8A4,4 0 0,1 12,12A4,4 0 0,1 8,8A4,4 0 0,1 12,4M12,14C16.42,14 20,15.79 20,18V20H4V18C4,15.79 7.58,14 12,14Z"/>
											</svg>
											<span>LDAP</span>
										</button>
									{/if}
							</div>

							<!-- OAuth 登录 -->
							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="relative">
									<div class="absolute inset-0 flex items-center">
										<div class="w-full border-t border-gray-200 dark:border-gray-700"></div>
									</div>
									<div class="relative flex justify-center text-sm">
										<span class="px-2 bg-gray-50/50 dark:bg-gray-800/50 text-gray-500">或使用</span>
									</div>
								</div>

								<div class="flex flex-wrap gap-2 justify-center">
									{#if $config?.oauth?.providers?.google}
											<button
												type="button"
												on:click={() => window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`}
												class="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-gray-50 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors text-sm border border-gray-200 dark:border-gray-600"
											>
												<svg class="w-4 h-4" viewBox="0 0 24 24">
													<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
													<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
													<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
													<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
												</svg>
												<span>Google</span>
											</button>
										{/if}

										{#if $config?.oauth?.providers?.github}
											<button
												type="button"
												on:click={() => window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`}
												class="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-gray-50 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors text-sm border border-gray-200 dark:border-gray-600"
											>
												<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
													<path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"/>
												</svg>
												<span>GitHub</span>
											</button>
										{/if}

										{#if $config?.oauth?.providers?.microsoft}
											<button
												type="button"
												on:click={() => window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`}
												class="flex items-center space-x-2 px-4 py-2 bg-white hover:bg-gray-50 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors text-sm border border-gray-200 dark:border-gray-600"
											>
												<svg class="w-4 h-4" viewBox="0 0 24 24">
													<path fill="#f25022" d="M1 1h10v10H1z"/>
													<path fill="#00a4ef" d="M13 1h10v10H13z"/>
													<path fill="#7fba00" d="M1 13h10v10H1z"/>
													<path fill="#ffb900" d="M13 13h10v10H13z"/>
												</svg>
												<span>Microsoft</span>
											</button>
										{/if}
								</div>
							{/if}
						</div>
					</div>
				{/if}
			</div>
		</div>

		<!-- 底部版权信息 -->
		<div class="absolute bottom-4 left-0 right-0 text-center text-xs text-gray-500 dark:text-gray-400">
			© {new Date().getFullYear()} {$WEBUI_NAME} · 简洁 · 安全 · 高效
		</div>
	{/if}
</div>

<style>
	:global(body) {
		@apply overflow-hidden;
	}

	/* 背景网格图案 */
	.bg-grid-pattern {
		background-image: 
			linear-gradient(to right, rgba(148, 163, 184, 0.1) 1px, transparent 1px),
			linear-gradient(to bottom, rgba(148, 163, 184, 0.1) 1px, transparent 1px);
		background-size: 20px 20px;
	}

	/* 卡片玻璃效果 */
	.backdrop-blur-xl {
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
	}

	/* 企业微信登录容器 */
	#wecom-login-container {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	/* 输入框焦点效果 */
	input:focus {
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	/* 按钮悬浮效果 - 仅对主要按钮生效 */
	button[type="submit"]:hover {
		transform: translateY(-1px);
	}

	/* 渐变动画 */
	@keyframes gradient-x {
		0%, 100% {
			background-size: 200% 200%;
			background-position: left center;
		}
		50% {
			background-size: 200% 200%;
			background-position: right center;
		}
	}

	/* 脉冲动画优化 */
	.animate-pulse {
		animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}

	@keyframes pulse {
		0%, 100% {
			opacity: 1;
		}
		50% {
			opacity: 0.7;
		}
	}

	/* 卡片阴影效果 */
	.shadow-xl {
		box-shadow: 
			0 20px 25px -5px rgba(0, 0, 0, 0.1),
			0 10px 10px -5px rgba(0, 0, 0, 0.04);
	}

	.dark .shadow-xl {
		box-shadow: 
			0 20px 25px -5px rgba(0, 0, 0, 0.25),
			0 10px 10px -5px rgba(0, 0, 0, 0.1);
	}

	/* 响应式设计 */
	@media (max-width: 640px) {
		#wecom-login-container {
			min-height: 180px;
		}
		
		.backdrop-blur-xl {
			backdrop-filter: blur(12px);
			-webkit-backdrop-filter: blur(12px);
		}
	}

	/* 深色模式优化 */
	@media (prefers-color-scheme: dark) {
		.bg-grid-pattern {
			background-image: 
				linear-gradient(to right, rgba(71, 85, 105, 0.1) 1px, transparent 1px),
				linear-gradient(to bottom, rgba(71, 85, 105, 0.1) 1px, transparent 1px);
		}
	}
</style>
