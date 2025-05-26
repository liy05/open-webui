# 聊天输入界面修改说明

## 修改目标
将上传文件和截图按钮从+号菜单中提取出来，放在+号外面右侧，用户无需点开+号菜单即可直接使用这些功能。

## 修改内容

### 1. MessageInput.svelte 主要修改

#### 新增图标导入
```typescript
import DocumentArrowUpSolid from '../icons/DocumentArrowUpSolid.svelte';
import CameraSolid from '../icons/CameraSolid.svelte';
```

#### 移除InputMenu的相关props
从InputMenu组件调用中移除了以下props：
- `{screenCaptureHandler}`
- `{inputFilesHandler}`
- `uploadFilesHandler={() => { filesInputElement.click(); }}`

#### 在右侧按钮区域新增截图和文件上传按钮
在语音录制按钮之前添加了：
- **截图按钮**：支持桌面端屏幕截图和移动端相机拍照
- **文件上传按钮**：直接触发文件选择对话框

#### 新增隐藏的相机输入元素
```html
<!-- Hidden file input used to open the camera on mobile -->
<input
    id="camera-input"
    type="file"
    accept="image/*"
    capture="environment"
    on:change={(event) => {
        const inputFiles = Array.from(event.target?.files);
        if (inputFiles && inputFiles.length > 0) {
            console.log(inputFiles);
            inputFilesHandler(inputFiles);
        }
    }}
    style="display: none;"
/>
```

### 2. InputMenu.svelte 主要修改

#### 移除不需要的props
- `export let screenCaptureHandler: Function;`
- `export let uploadFilesHandler: Function;`
- `export let inputFilesHandler: Function;`

#### 移除不需要的导入
- `import DocumentArrowUpSolid from '$lib/components/icons/DocumentArrowUpSolid.svelte';`
- `import CameraSolid from '$lib/components/icons/CameraSolid.svelte';`

#### 移除截图和文件上传菜单项
完全移除了截图和文件上传的DropdownMenu.Item组件

#### 移除相关变量和函数
- `let fileUploadEnabled = true;`
- `$: fileUploadEnabled = $user?.role === 'admin' || $user?.permissions?.chat?.file_upload;`
- `const detectMobile = () => { ... }`
- `function handleFileChange(event) { ... }`
- 隐藏的相机输入元素

#### 优化分隔线显示逻辑
只有在Google Drive或OneDrive集成启用时才显示分隔线

## 功能保持
- 所有原有功能保持不变
- 权限检查机制保持不变
- 移动端和桌面端的兼容性保持不变
- Google Drive和OneDrive集成功能保持在+号菜单中

## 用户体验改进
1. **更直观的操作**：用户可以直接看到并点击截图和文件上传按钮
2. **减少点击步骤**：无需先点击+号再选择功能
3. **更清晰的界面**：常用功能直接暴露，+号菜单专注于高级功能（工具选择、云存储集成）

## 技术实现细节
- 保持了原有的权限检查逻辑
- 保持了移动端检测和相机调用逻辑
- 保持了文件处理和上传逻辑
- 优化了组件间的props传递，减少了不必要的依赖 