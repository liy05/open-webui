<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher } from 'svelte';
	import { onMount, getContext } from 'svelte';
	import { addUser } from '$lib/apis/auths';

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Modal from '$lib/components/common/Modal.svelte';
	import { generateInitialsImage } from '$lib/utils';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let loading = false;
	let tab = '';
	let inputFiles;

	let _user = {
		name: '',
		email: '',
		password: '',
		role: 'user',
		phone_number: ''
	};

	$: if (show) {
		_user = {
			name: '',
			email: '',
			password: '',
			role: 'user',
			phone_number: ''
		};
	}

	const submitHandler = async () => {
		const stopLoading = () => {
			dispatch('save');
			loading = false;
		};

		if (tab === '') {
			loading = true;

			const res = await addUser(
				localStorage.token,
				_user.name,
				_user.email,
				_user.password,
				_user.role,
				generateInitialsImage(_user.name),
				_user.phone_number
			).catch((error) => {
				toast.error(`${error}`);
			});

			if (res) {
				stopLoading();
				show = false;
			}
		} else {
			if (inputFiles) {
				loading = true;

				const file = inputFiles[0];
				const reader = new FileReader();

				reader.onload = async (e) => {
					try {
						const csv = e.target.result;
						const rows = parseCSV(csv);

						let userCount = 0;

						for (const [idx, columns] of rows.entries()) {
							console.log(idx, columns);

							if (idx > 0) {
								if (
									columns.length >= 4 &&
									['admin', 'user', 'pending'].includes((columns[3] || '').toLowerCase())
								) {
									const name = columns[0] || '';
									const email = columns[1] || '';
									const password = columns[2] || '';
									const role = (columns[3] || '').toLowerCase();
									const phoneNumber = columns[4] || '';

									console.log('添加用户', { name, email, role, phoneNumber });

									const res = await addUser(
										localStorage.token,
										name,
										email,
										password,
										role,
										generateInitialsImage(name),
										phoneNumber
									).catch((error) => {
										toast.error(`Row ${idx + 1}: ${error}`);
										return null;
									});

									if (res) {
										userCount = userCount + 1;
									}
								} else {
									toast.error(`Row ${idx + 1}: invalid format.`);
								}
							}
						}

						toast.success(`Successfully imported ${userCount} users.`);
						inputFiles = null;
						const uploadInputElement = document.getElementById('upload-user-csv-input');

						if (uploadInputElement) {
							uploadInputElement.value = null;
						}

						stopLoading();
					} catch (error) {
						console.error('导入错误:', error);
						toast.error(`Import error: ${error.message}`);
						stopLoading();
					}
				};

				// 尝试使用多种编码格式读取CSV文件
				try {
					// 首先尝试检测文件编码
					const headerBytes = await readFileHeader(file);
					const encoding = detectEncoding(headerBytes);
					reader.readAsText(file, encoding);
				} catch (error) {
					// 如果检测失败，尝试常见的编码
					reader.readAsText(file, 'utf-8');
				}
			} else {
				toast.error($i18n.t('File not found.'));
			}
		}

		loading = false;
	};

	const parseCSV = (text) => {
		const result = [];
		let row = [];
		let insideQuotes = false;
		let currentValue = '';

		for (let i = 0; i < text.length; i++) {
			const char = text[i];
			const nextChar = text[i + 1];

			if (char === '"') {
				if (insideQuotes && nextChar === '"') {
					currentValue += '"';
					i++;
				} else {
					insideQuotes = !insideQuotes;
				}
			} else if (char === ',' && !insideQuotes) {
				row.push(currentValue.trim());
				currentValue = '';
			} else if ((char === '\r' || char === '\n') && !insideQuotes) {
				if (currentValue.trim() !== '' || row.length > 0) {
					row.push(currentValue.trim());
					result.push(row);
					row = [];
					currentValue = '';
				}
				if (char === '\r' && nextChar === '\n') {
					i++;
				}
			} else {
				currentValue += char;
			}
		}

		if (currentValue.trim() !== '' || row.length > 0) {
			row.push(currentValue.trim());
			result.push(row);
		}

		return result;
	};

	const readFileHeader = (file) => {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (e) => {
				const buffer = e.target.result;
				resolve(new Uint8Array(buffer));
			};
			reader.onerror = reject;
			reader.readAsArrayBuffer(file.slice(0, 4096)); // 读取文件前4KB
		});
	};

	const detectEncoding = (bytes) => {
		// 检测BOM标记
		if (bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf) {
			return 'utf-8';
		}
		if (bytes.length >= 2 && bytes[0] === 0xff && bytes[1] === 0xfe) {
			return 'utf-16le';
		}
		if (bytes.length >= 2 && bytes[0] === 0xfe && bytes[1] === 0xff) {
			return 'utf-16be';
		}

		// 检测中文编码 (简化版)
		// 如果文件中包含大量在GB18030范围内但UTF-8无效的字节序列，可能是GB18030编码
		let gbCount = 0;
		let utfCount = 0;

		for (let i = 0; i < bytes.length - 1; i++) {
			// 可能的GB2312/GBK/GB18030字节
			if (bytes[i] >= 0x81 && bytes[i] <= 0xfe && bytes[i + 1] >= 0x40 && bytes[i + 1] <= 0xfe) {
				gbCount++;
			}

			// 可能的UTF-8字节
			if (
				(bytes[i] >= 0xc0 && bytes[i] <= 0xdf && bytes[i + 1] >= 0x80 && bytes[i + 1] <= 0xbf) ||
				(bytes[i] >= 0xe0 &&
					bytes[i] <= 0xef &&
					i + 2 < bytes.length &&
					bytes[i + 1] >= 0x80 &&
					bytes[i + 1] <= 0xbf &&
					bytes[i + 2] >= 0x80 &&
					bytes[i + 2] <= 0xbf)
			) {
				utfCount++;
			}
		}

		if (gbCount > utfCount) {
			return 'gb18030'; // GB18030 兼容 GBK 和 GB2312
		}

		return 'utf-8'; // 默认使用UTF-8
	};
</script>

<Modal size="sm" bind:show>
	<div>
		<div class=" flex justify-between dark:text-gray-300 px-5 pt-4 pb-2">
			<div class=" text-lg font-medium self-center">{$i18n.t('Add User')}</div>
			<button
				class="self-center"
				on:click={() => {
					show = false;
				}}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="w-5 h-5"
				>
					<path
						d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
					/>
				</svg>
			</button>
		</div>

		<div class="flex flex-col md:flex-row w-full px-4 pb-3 md:space-x-4 dark:text-gray-200">
			<div class=" flex flex-col w-full sm:flex-row sm:justify-center sm:space-x-6">
				<form
					class="flex flex-col w-full"
					on:submit|preventDefault={() => {
						submitHandler();
					}}
				>
					<div
						class="flex -mt-2 mb-1.5 gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent dark:text-gray-200"
					>
						<button
							class="min-w-fit rounded-full p-1.5 {tab === ''
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							type="button"
							on:click={() => {
								tab = '';
							}}>{$i18n.t('Form')}</button
						>

						<button
							class="min-w-fit rounded-full p-1.5 {tab === 'import'
								? ''
								: 'text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							type="button"
							on:click={() => {
								tab = 'import';
							}}>{$i18n.t('CSV Import')}</button
						>
					</div>

					<div class="px-1">
						{#if tab === ''}
							<div class="flex flex-col w-full mb-3">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Role')}</div>

								<div class="flex-1">
									<select
										class="w-full capitalize rounded-lg text-sm bg-transparent dark:disabled:text-gray-500 outline-hidden"
										bind:value={_user.role}
										placeholder={$i18n.t('Enter Your Role')}
										required
									>
										<option value="pending"> {$i18n.t('pending')} </option>
										<option value="user"> {$i18n.t('user')} </option>
										<option value="admin"> {$i18n.t('admin')} </option>
									</select>
								</div>
							</div>

							<div class="flex flex-col w-full mt-1">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Name')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="text"
										bind:value={_user.name}
										placeholder={$i18n.t('Enter Your Full Name')}
										autocomplete="off"
										required
									/>
								</div>
							</div>

							<hr class=" border-gray-100 dark:border-gray-850 my-2.5 w-full" />

							<div class="flex flex-col w-full">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Email')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="email"
										bind:value={_user.email}
										placeholder={$i18n.t('Enter Your Email')}
										required
									/>
								</div>
							</div>

							<div class="flex flex-col w-full mt-1">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Password')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="password"
										bind:value={_user.password}
										placeholder={$i18n.t('Enter Your Password')}
										autocomplete="off"
									/>
								</div>
							</div>

							<div class="flex flex-col w-full mt-1">
								<div class=" mb-1 text-xs text-gray-500">{$i18n.t('Phone Number')}</div>

								<div class="flex-1">
									<input
										class="w-full text-sm bg-transparent disabled:text-gray-500 dark:disabled:text-gray-500 outline-hidden"
										type="text"
										bind:value={_user.phone_number}
										placeholder={$i18n.t('Enter Your Phone Number')}
									/>
								</div>
							</div>
						{:else if tab === 'import'}
							<div>
								<div class="mb-3 w-full">
									<input
										id="upload-user-csv-input"
										hidden
										bind:files={inputFiles}
										type="file"
										accept=".csv"
									/>

									<button
										class="w-full text-sm font-medium py-3 bg-transparent hover:bg-gray-100 border border-dashed dark:border-gray-850 dark:hover:bg-gray-850 text-center rounded-xl"
										type="button"
										on:click={() => {
											document.getElementById('upload-user-csv-input')?.click();
										}}
									>
										{#if inputFiles}
											{inputFiles.length > 0 ? `${inputFiles.length}` : ''} document(s) selected.
										{:else}
											{$i18n.t('Click here to select a csv file.')}
										{/if}
									</button>
								</div>

								<div class=" text-xs text-gray-500">
									ⓘ {$i18n.t(
										'Ensure your CSV file includes 5 columns in this order: Name, Email, Password, Role, Phone Number (optional).'
									)}
									<a
										class="underline dark:text-gray-200"
										href="{WEBUI_BASE_URL}/static/user-import.csv"
									>
										{$i18n.t('Click here to download user import template file.')}
									</a>
								</div>
							</div>
						{/if}
					</div>

					<div class="flex justify-end pt-3 text-sm font-medium">
						<button
							class="px-3.5 py-1.5 text-sm font-medium bg-black hover:bg-gray-900 text-white dark:bg-white dark:text-black dark:hover:bg-gray-100 transition rounded-full flex flex-row space-x-1 items-center {loading
								? ' cursor-not-allowed'
								: ''}"
							type="submit"
							disabled={loading}
						>
							{$i18n.t('Save')}

							{#if loading}
								<div class="ml-2 self-center">
									<svg
										class=" w-4 h-4"
										viewBox="0 0 24 24"
										fill="currentColor"
										xmlns="http://www.w3.org/2000/svg"
										><style>
											.spinner_ajPY {
												transform-origin: center;
												animation: spinner_AtaB 0.75s infinite linear;
											}
											@keyframes spinner_AtaB {
												100% {
													transform: rotate(360deg);
												}
											}
										</style><path
											d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
											opacity=".25"
										/><path
											d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
											class="spinner_ajPY"
										/></svg
									>
								</div>
							{/if}
						</button>
					</div>
				</form>
			</div>
		</div>
	</div>
</Modal>

<style>
	input::-webkit-outer-spin-button,
	input::-webkit-inner-spin-button {
		/* display: none; <- Crashes Chrome on hover */
		-webkit-appearance: none;
		margin: 0; /* <-- Apparently some margin are still there even though it's hidden */
	}

	.tabs::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.tabs {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}

	input[type='number'] {
		-moz-appearance: textfield; /* Firefox */
	}
</style>
