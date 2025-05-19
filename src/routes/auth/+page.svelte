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
		phoneSignIn
	} from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'phone';

	let name = '';
	let email = '';
	let password = '';
	let phoneNumber = '';
	let verificationCode = '';
	let countDown = 0;
	let intervalId: number | null = null;

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

	const sendSmsCodeHandler = async () => {
		if (countDown > 0) return;

		if (!phoneNumber || phoneNumber.length !== 11 || !/^\d+$/.test(phoneNumber)) {
			toast.error($i18n.t('请输入有效的手机号码'));
			return;
		}

		await sendSmsCode(phoneNumber).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

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
	};

	const submitHandler = async () => {
		if (mode === 'phone') {
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

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

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
		await checkOauthCallback();

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

<div class="w-full h-screen max-h-[100dvh] relative overflow-hidden bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-950">
	<div class="absolute inset-0 bg-pattern opacity-10 dark:opacity-5"></div>
	
	<!-- Decorative elements -->
	<div class="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-purple-200 dark:bg-purple-900/20 blur-3xl"></div>
	<div class="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-blue-200 dark:bg-blue-900/20 blur-3xl"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-50" />

	{#if loaded}
		<div class="fixed m-10 z-50">
			<div class="flex space-x-2">
				<div class="self-center flex items-center">
					<img
						id="logo"
						crossorigin="anonymous"
						src="/static/logo.svg"
						class="w-12 h-12 drop-shadow-lg"
						alt="Open WebUI Logo"
					/>
					<span class="ml-3 text-xl font-bold text-gray-800 dark:text-white">{$WEBUI_NAME}</span>
				</div>
			</div>
		</div>

		<div class="fixed bg-transparent min-h-screen w-full flex justify-center font-primary z-50 text-black dark:text-white">
			<div class="w-full sm:max-w-md px-10 min-h-screen flex flex-col text-center">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class="my-auto pb-10 w-full">
						<div class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold dark:text-gray-200">
							<div>
								{$i18n.t('正在登录到 {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
							</div>
							<div><Spinner /></div>
						</div>
					</div>
				{:else}
					<div class="my-auto pb-10 w-full dark:text-gray-100">
						<form
							class="flex flex-col justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg p-8 rounded-3xl shadow-lg border border-gray-200 dark:border-gray-800"
							on:submit={(e) => {
								e.preventDefault();
								submitHandler();
							}}
						>
							<div class="mb-6">
								<div class="text-2xl font-bold">
									{#if $config?.onboarding ?? false}
										{$i18n.t(`开始使用 {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
									{:else if mode === 'ldap'}
										{$i18n.t(`使用LDAP登录 {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
									{:else if mode === 'signin'}
										{$i18n.t(`{{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
									{:else if mode === 'phone'}
										{$i18n.t(`{{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
									{:else}
										{$i18n.t(`注册 {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
									{/if}
								</div>

								{#if ($config?.onboarding ?? false) && !($config?.features.auth_trusted_header ?? false) && $config?.features.auth !== false}
									<div class="mt-2 text-sm font-medium text-gray-600 dark:text-gray-400">
										ⓘ {$WEBUI_NAME}
										{$i18n.t('不会建立任何外部连接，您的数据安全地存储在本地托管的服务器上。')}
									</div>
								{/if}
							</div>

							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								<div class="flex flex-col mt-2 space-y-4">
									{#if mode === 'signup'}
										<div>
											<label for="name" class="text-sm font-medium text-left mb-1.5 block"
												>{$i18n.t('姓名')}</label
											>
											<input
												bind:value={name}
												type="text"
												id="name"
												class="w-full px-4 py-2.5 text-sm rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
												autocomplete="name"
												placeholder={$i18n.t('请输入您的全名')}
												required
											/>
										</div>
									{/if}

									{#if mode === 'ldap'}
										<div>
											<label for="username" class="text-sm font-medium text-left mb-1.5 block"
												>{$i18n.t('用户名')}</label
											>
											<input
												bind:value={ldapUsername}
												type="text"
												class="w-full px-4 py-2.5 text-sm rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
												autocomplete="username"
												name="username"
												id="username"
												placeholder={$i18n.t('请输入您的用户名')}
												required
											/>
										</div>
									{:else if mode === 'phone'}
										<div>
											<label for="phone_number" class="text-sm font-medium text-left mb-1.5 block"
												>{$i18n.t('手机号码')}</label
											>
											<input
												bind:value={phoneNumber}
												type="tel"
												id="phone_number"
												class="w-full px-4 py-2.5 text-sm rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
												autocomplete="tel"
												name="tel"
												placeholder={$i18n.t('请输入手机号码')}
												required
											/>
										</div>
										<div>
											<label
												for="verification_code"
												class="text-sm font-medium text-left mb-1.5 block">{$i18n.t('验证码')}</label
											>
											<div class="flex">
												<input
													bind:value={verificationCode}
													type="text"
													id="verification_code"
													class="w-full px-4 py-2.5 text-sm rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
													placeholder={$i18n.t('请输入验证码')}
													autocomplete="one-time-code"
													required
												/>
												<button
													type="button"
													class="text-sm px-4 py-2.5 ml-2 bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl whitespace-nowrap hover:bg-gray-200 dark:hover:bg-gray-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
													on:click={sendSmsCodeHandler}
													disabled={countDown > 0}
												>
													{countDown > 0 ? `${countDown}秒` : $i18n.t('获取验证码')}
												</button>
											</div>
										</div>
									{:else}
										<div>
											<label for="email" class="text-sm font-medium text-left mb-1.5 block"
												>{$i18n.t('邮箱')}</label
											>
											<input
												bind:value={email}
												type="email"
												id="email"
												class="w-full px-4 py-2.5 text-sm rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
												autocomplete="email"
												name="email"
												placeholder={$i18n.t('请输入您的邮箱')}
												required
											/>
										</div>
									{/if}

									{#if mode !== 'phone'}
										<div>
											<label for="password" class="text-sm font-medium text-left mb-1.5 block"
												>{$i18n.t('密码')}</label
											>
											<input
												bind:value={password}
												type="password"
												id="password"
												class="w-full px-4 py-2.5 text-sm rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
												placeholder={$i18n.t('请输入您的密码')}
												autocomplete="current-password"
												name="current-password"
												required
											/>
										</div>
									{/if}
								</div>
							{/if}

							<div class="mt-6">
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									{#if mode === 'ldap'}
										<button
											class="bg-blue-600 hover:bg-blue-700 text-white transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm shadow-blue-500/20 hover:shadow-md"
											type="submit"
										>
											{$i18n.t('认证')}
										</button>
									{:else if mode === 'phone'}
										<button
											class="bg-blue-600 hover:bg-blue-700 text-white transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm shadow-blue-500/20 hover:shadow-md"
											type="submit"
										>
											{$i18n.t('验证并登录')}
										</button>
									{:else}
										<button
											class="bg-blue-600 hover:bg-blue-700 text-white transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm shadow-blue-500/20 hover:shadow-md"
											type="submit"
										>
											{mode === 'signin'
												? $i18n.t('登录')
												: ($config?.onboarding ?? false)
													? $i18n.t('创建管理员账户')
													: $i18n.t('创建账户')}
										</button>

										{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
											<div class="mt-4 text-sm text-center">
												{mode === 'signin' ? $i18n.t('没有账户?') : $i18n.t('已有账户?')}

												<button
													class="font-medium text-blue-600 dark:text-blue-400 hover:underline ml-1"
													type="button"
													on:click={() => {
														if (mode === 'signin') {
															mode = 'signup';
														} else {
															mode = 'signin';
														}
													}}
												>
													{mode === 'signin' ? $i18n.t('注册') : $i18n.t('登录')}
												</button>
											</div>
										{/if}
									{/if}
								{/if}
							</div>
						</form>

						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="inline-flex items-center justify-center w-full mt-6">
								<hr class="w-32 h-px my-4 border-0 dark:bg-gray-700 bg-gray-300" />
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									<span
										class="px-3 text-sm font-medium text-gray-700 dark:text-gray-300 bg-transparent"
										>{$i18n.t('或')}</span
									>
								{/if}
								<hr class="w-32 h-px my-4 border-0 dark:bg-gray-700 bg-gray-300" />
							</div>
							
							<div class="flex flex-col space-y-3 mt-2 bg-white/80 dark:bg-gray-900/80 backdrop-blur-lg p-6 rounded-3xl shadow-lg border border-gray-200 dark:border-gray-800">
								<div class="text-sm font-medium mb-1">{$i18n.t('使用以下方式快速登录')}</div>
								
								{#if $config?.oauth?.providers?.google}
									<button
										class="flex justify-center items-center bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm hover:shadow-md"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-5 mr-3">
											<path
												fill="#EA4335"
												d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
											/><path
												fill="#4285F4"
												d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
											/><path
												fill="#FBBC05"
												d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
											/><path
												fill="#34A853"
												d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
											/><path fill="none" d="M0 0h48v48H0z" />
										</svg>
										<span>{$i18n.t('使用 {{provider}} 继续', { provider: 'Google' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										class="flex justify-center items-center bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm hover:shadow-md"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-5 mr-3">
											<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
												x="1"
												y="11"
												width="9"
												height="9"
												fill="#00a4ef"
											/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
												x="11"
												y="11"
												width="9"
												height="9"
												fill="#ffb900"
											/>
										</svg>
										<span>{$i18n.t('使用 {{provider}} 继续', { provider: 'Microsoft' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										class="flex justify-center items-center bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm hover:shadow-md"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-5 mr-3">
											<path
												fill="currentColor"
												d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
											/>
										</svg>
										<span>{$i18n.t('使用 {{provider}} 继续', { provider: 'GitHub' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										class="flex justify-center items-center bg-white hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-800 dark:text-gray-200 border border-gray-200 dark:border-gray-700 transition w-full rounded-xl font-medium text-sm py-2.5 shadow-sm hover:shadow-md"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-5 mr-3"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
											/>
										</svg>

										<span
											>{$i18n.t('使用 {{provider}} 继续', {
												provider: $config?.oauth?.providers?.oidc ?? 'SSO'
											})}</span
										>
									</button>
								{/if}
							</div>
						{/if}

						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<div class="mt-4">
								<button
									class="flex justify-center items-center text-sm w-full text-center text-blue-600 dark:text-blue-400 hover:underline"
									type="button"
									on:click={() => {
										if (mode === 'ldap')
											mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
										else mode = 'ldap';
									}}
								>
									<span>{mode === 'ldap' ? $i18n.t('使用邮箱继续') : $i18n.t('使用LDAP继续')}</span>
								</button>
							</div>
						{/if}

						<div class="mt-4">
							<button
								class="flex justify-center items-center text-sm w-full text-center text-blue-600 dark:text-blue-400 hover:underline"
								type="button"
								on:click={() => {
									if (mode === 'phone') mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
									else mode = 'phone';
								}}
							>
								<span>{mode === 'phone' ? $i18n.t('使用邮箱继续') : $i18n.t('使用手机号继续')}</span
								>
							</button>
						</div>
					</div>
				{/if}
			</div>
		</div>
		
		<!-- 版权信息 -->
		<div class="fixed bottom-4 left-0 right-0 text-center text-xs text-gray-500 dark:text-gray-600">
			© {new Date().getFullYear()} {$WEBUI_NAME}
		</div>
	{/if}
</div>

<style>
	:global(body) {
		@apply overflow-hidden;
	}
	
	.bg-pattern {
		background-image: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
	}
	
	input {
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
	}
	
	.dark input {
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
	}
	
	/* 自定义输入框样式 */
	input:focus {
		@apply outline-none;
		animation: pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}
	
	@keyframes pulse {
		0%, 100% {
			box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.2);
		}
		50% {
			box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.2);
		}
	}
</style>
