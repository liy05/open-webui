<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Switch from '$lib/components/common/Switch.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let saveHandler: Function;

	// 企业微信配置
	let ENABLE_WECOM_AUTH = false;
	let WECOM_CONFIG = {
		corp_id: '',
		agent_id: '',
		secret: '',
		redirect_uri: ''
	};

	let loading = false;

	const getWeComConfig = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/wecom`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const data = await res.json();
				ENABLE_WECOM_AUTH = data.ENABLE_WECOM_AUTH;
			}
		} catch (error) {
			console.error('Failed to fetch WeChat config:', error);
		}
	};

	const getWeComServerConfig = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/wecom/server`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (res.ok) {
				const data = await res.json();
				WECOM_CONFIG = {
					corp_id: data.corp_id || '',
					agent_id: data.agent_id || '',
					secret: data.secret || '',
					redirect_uri: data.redirect_uri || ''
				};
			}
		} catch (error) {
			console.error('Failed to fetch WeChat server config:', error);
		}
	};

	const updateWeComConfig = async () => {
		loading = true;
		
		try {
			// 更新企业微信开关配置
			const enableRes = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/wecom`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({
					enable_wecom_auth: ENABLE_WECOM_AUTH
				})
			});

			if (!enableRes.ok) {
				throw new Error('Failed to update WeChat auth config');
			}

			// 如果启用了企业微信，更新服务器配置
			if (ENABLE_WECOM_AUTH) {
				const serverRes = await fetch(`${WEBUI_API_BASE_URL}/auths/admin/config/wecom/server`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.token}`
					},
					body: JSON.stringify(WECOM_CONFIG)
				});

				if (!serverRes.ok) {
					throw new Error('Failed to update WeChat server config');
				}
			}

			toast.success('企业微信配置已保存');
			if (saveHandler) {
				saveHandler();
			}
		} catch (error) {
			console.error('Failed to update WeChat config:', error);
			toast.error('企业微信配置保存失败');
		} finally {
			loading = false;
		}
	};

	// 添加响应式声明来调试状态变化
	$: {
		console.log('ENABLE_WECOM_AUTH changed:', ENABLE_WECOM_AUTH);
	}

	onMount(async () => {
		await Promise.all([
			getWeComConfig(),
			getWeComServerConfig()
		]);
	});
</script>

<div class="mb-3.5">
	<div class="mb-2.5 text-base font-medium">企业微信认证配置</div>
	
	<hr class="border-gray-100 dark:border-gray-850 my-2" />

	<div class="space-y-3">
		<!-- 启用企业微信认证开关 -->
		<div class="flex w-full justify-between items-center">
			<div class="text-xs pr-2">
				<div class="">启用企业微信认证</div>
				<div class="text-xs text-gray-500">
					允许用户通过企业微信账号登录系统
				</div>
			</div>
			<Switch bind:state={ENABLE_WECOM_AUTH} />
		</div>

		{#if !ENABLE_WECOM_AUTH}
			<div class="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-3">
				<div class="text-xs text-yellow-800 dark:text-yellow-200">
					<strong>提示：</strong> 请先启用企业微信认证，然后配置以下参数。
				</div>
			</div>
		{/if}

		<!-- 企业微信配置字段 -->
		<div class="space-y-3 {ENABLE_WECOM_AUTH ? '' : 'opacity-60'}">
			<!-- 企业ID -->
			<div class="mb-2.5">
				<label class="block mb-1 text-xs font-medium" for="wecom-corp-id">
					企业ID (Corp ID)
				</label>
				<input
					id="wecom-corp-id"
					bind:value={WECOM_CONFIG.corp_id}
					class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
					placeholder="例如：wwd1234567890abcdef"
					disabled={!ENABLE_WECOM_AUTH}
					required
				/>
				<div class="text-xs text-gray-500 mt-1">
					在企业微信管理后台的"我的企业"页面可以找到企业ID
				</div>
			</div>

			<!-- 应用ID -->
			<div class="mb-2.5">
				<label class="block mb-1 text-xs font-medium" for="wecom-agent-id">
					应用ID (Agent ID)
				</label>
				<input
					id="wecom-agent-id"
					bind:value={WECOM_CONFIG.agent_id}
					class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
					placeholder="例如：1000001"
					disabled={!ENABLE_WECOM_AUTH}
					required
				/>
				<div class="text-xs text-gray-500 mt-1">
					在企业微信应用详情页面可以找到AgentID
				</div>
			</div>

			<!-- 应用Secret -->
			<div class="mb-2.5">
				<label class="block mb-1 text-xs font-medium" for="wecom-secret">
					应用Secret
				</label>
				<SensitiveInput
					id="wecom-secret"
					bind:value={WECOM_CONFIG.secret}
					placeholder="应用的Secret密钥"
					readOnly={!ENABLE_WECOM_AUTH}
					required
				/>
				<div class="text-xs text-gray-500 mt-1">
					在企业微信应用详情页面可以找到Secret，请妥善保管
				</div>
			</div>

			<!-- 回调URL -->
			<div class="mb-2.5">
				<label class="block mb-1 text-xs font-medium" for="wecom-redirect-uri">
					授权回调URL
				</label>
				<input
					id="wecom-redirect-uri"
					bind:value={WECOM_CONFIG.redirect_uri}
					class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
					placeholder="{WEBUI_API_BASE_URL}/auths/wecom/callback"
					disabled={!ENABLE_WECOM_AUTH}
					required
				/>
				<div class="text-xs text-gray-500 mt-1">
					在企业微信应用设置中配置此回调URL为可信域名
				</div>
			</div>

			<!-- 配置说明 -->
			<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
				<div class="text-xs font-medium text-blue-800 dark:text-blue-200 mb-2">
					配置说明：
				</div>
				<div class="text-xs text-blue-700 dark:text-blue-300 space-y-1">
					<div>1. 在企业微信管理后台创建自建应用</div>
					<div>2. 设置可信域名为你的Open WebUI域名</div>
					<div>3. 配置网页授权回调域为上述回调URL</div>
					<div>4. 确保应用有读取用户信息的权限</div>
					<div>5. 用户需要先在Open WebUI注册并设置手机号</div>
				</div>
			</div>
		</div>

		<!-- 测试连接 -->
		{#if ENABLE_WECOM_AUTH && WECOM_CONFIG.corp_id && WECOM_CONFIG.agent_id && WECOM_CONFIG.secret}
			<div class="flex justify-between items-center">
				<div class="text-xs">
					<div class="">测试企业微信连接</div>
					<div class="text-xs text-gray-500">
						验证配置是否正确
					</div>
				</div>
				<a
					href="{WEBUI_API_BASE_URL}/auths/wecom/login"
					target="_blank"
					class="text-xs px-3 py-1.5 bg-blue-50 hover:bg-blue-100 dark:bg-blue-900/20 dark:hover:bg-blue-800/30 transition rounded-lg font-medium text-blue-700 dark:text-blue-300"
				>
					测试登录
				</a>
			</div>
		{/if}
	</div>

	<!-- 保存按钮 -->
	<div class="flex justify-end mt-4">
		<button
			class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-lg disabled:opacity-50"
			on:click={updateWeComConfig}
			disabled={loading}
			type="button"
		>
			{loading ? '保存中...' : '保存企业微信配置'}
		</button>
	</div>
</div> 