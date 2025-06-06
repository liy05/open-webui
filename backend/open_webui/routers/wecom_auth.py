import logging
import json
import time
import datetime
from typing import Optional
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, HTTPException, Request, Response, Depends, status
from fastapi.responses import RedirectResponse, HTMLResponse

from open_webui.models.auths import WeComAuthForm
from open_webui.routers.auths import SessionUserResponse
from open_webui.models.users import Users
from open_webui.constants import ERROR_MESSAGES
from open_webui.config import (
    WECOM_CORP_ID,
    WECOM_AGENT_ID, 
    WECOM_SECRET,
    WECOM_REDIRECT_URI,
    ENABLE_WECOM_AUTH,
)
from open_webui.env import (
    WEBUI_AUTH_COOKIE_SAME_SITE,
    WEBUI_AUTH_COOKIE_SECURE,
)
from open_webui.utils.auth import (
    create_token,
    get_current_user,
    decode_token,
)
from open_webui.utils.access_control import get_permissions

router = APIRouter()

log = logging.getLogger(__name__)

############################
# 企业微信网页授权登录
############################

class WeComAPI:
    """企业微信API封装类"""
    
    def __init__(self, corp_id: str, secret: str):
        self.corp_id = corp_id
        self.secret = secret
        self.access_token = None
        self.token_expires_at = 0
    
    def get_access_token(self) -> str:
        """获取access_token"""
        current_time = time.time()
        
        # 如果token未过期，直接返回
        if self.access_token and current_time < self.token_expires_at:
            return self.access_token
        
        # 请求新的access_token
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("errcode") == 0:
                self.access_token = data["access_token"]
                # 提前5分钟过期，确保安全
                self.token_expires_at = current_time + data["expires_in"] - 300
                return self.access_token
            else:
                log.error(f"获取access_token失败: {data}")
                raise HTTPException(
                    status_code=500,
                    detail=f"获取企业微信access_token失败: {data.get('errmsg', '未知错误')}"
                )
        except requests.RequestException as e:
            log.error(f"请求企业微信API失败: {e}")
            raise HTTPException(status_code=500, detail="网络请求失败")
    
    def get_user_info(self, code: str) -> dict:
        """通过code获取用户信息"""
        access_token = self.get_access_token()
        
        # 第一步：通过code换取用户信息
        url = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
        params = {
            "access_token": access_token,
            "code": code
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("errcode") == 0:
                return data
            else:
                log.error(f"获取用户信息失败: {data}")
                raise HTTPException(
                    status_code=400,
                    detail=f"获取用户信息失败: {data.get('errmsg', '未知错误')}"
                )
        except requests.RequestException as e:
            log.error(f"请求企业微信API失败: {e}")
            raise HTTPException(status_code=500, detail="网络请求失败")
    
    def get_user_detail(self, userid: str) -> dict:
        """获取用户详细信息"""
        access_token = self.get_access_token()
        
        url = "https://qyapi.weixin.qq.com/cgi-bin/user/get"
        params = {
            "access_token": access_token,
            "userid": userid
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("errcode") == 0:
                return data
            else:
                log.error(f"获取用户详细信息失败: {data}")
                raise HTTPException(
                    status_code=400,
                    detail=f"获取用户详细信息失败: {data.get('errmsg', '未知错误')}"
                )
        except requests.RequestException as e:
            log.error(f"请求企业微信API失败: {e}")
            raise HTTPException(status_code=500, detail="网络请求失败")
    
    def get_user_sensitive_info(self, user_ticket: str) -> dict:
        """获取用户敏感信息（包含手机号）"""
        access_token = self.get_access_token()
        
        url = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserdetail"
        data = {
            "user_ticket": user_ticket
        }
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                f"{url}?access_token={access_token}",
                json=data,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("errcode") == 0:
                return data
            else:
                log.error(f"获取用户敏感信息失败: {data}")
                raise HTTPException(
                    status_code=400,
                    detail=f"获取用户敏感信息失败: {data.get('errmsg', '未知错误')}"
                )
        except requests.RequestException as e:
            log.error(f"请求企业微信API失败: {e}")
            raise HTTPException(status_code=500, detail="网络请求失败")


@router.get("/login")
async def wecom_login(request: Request):
    """构造企业微信网页授权链接并重定向"""
    if not ENABLE_WECOM_AUTH.value:
        raise HTTPException(status_code=400, detail="企业微信认证未启用")
    
    if not all([WECOM_CORP_ID.value, WECOM_AGENT_ID.value, WECOM_REDIRECT_URI.value]):
        raise HTTPException(
            status_code=500, 
            detail="企业微信配置不完整，请联系管理员"
        )
    
    # 构造授权链接
    auth_url = "https://open.weixin.qq.com/connect/oauth2/authorize"
    params = {
        "appid": WECOM_CORP_ID.value,
        "redirect_uri": WECOM_REDIRECT_URI.value,
        "response_type": "code",
        "scope": "snsapi_privateinfo",  # 使用 snsapi_privateinfo 来获取敏感信息
        "agentid": WECOM_AGENT_ID.value,
        "state": "openwebui_auth"
    }
    
    # 构造完整的授权URL
    auth_full_url = f"{auth_url}?{urlencode(params)}#wechat_redirect"
    
    log.info(f"重定向到企业微信授权页面: {auth_full_url}")
    return RedirectResponse(url=auth_full_url)


@router.get("/callback")
async def wecom_callback(request: Request, response: Response, code: str, state: str = None):
    """企业微信授权回调处理"""
    if not ENABLE_WECOM_AUTH.value:
        raise HTTPException(status_code=400, detail="企业微信认证未启用")
    
    if not code:
        raise HTTPException(status_code=400, detail="授权失败，未获取到授权码")
    
    if state != "openwebui_auth":
        raise HTTPException(status_code=400, detail="非法的授权请求")
    
    try:
        # 初始化企业微信API
        wecom_api = WeComAPI(WECOM_CORP_ID.value, WECOM_SECRET.value)
        
        # 第一步：通过code获取用户信息
        user_info = wecom_api.get_user_info(code)
        log.info(f"获取到用户信息: {user_info}")
        
        userid = user_info.get("userid")
        user_ticket = user_info.get("user_ticket")  # 获取user_ticket
        
        if not userid:
            # 如果是非企业成员，可能需要使用openid
            openid = user_info.get("openid")
            if not openid:
                raise HTTPException(
                    status_code=400,
                    detail="无法获取用户标识，可能不是企业成员"
                )
            # 对于非企业成员，我们暂时不支持登录
            raise HTTPException(
                status_code=400,
                detail="只支持企业成员登录"
            )
        
        # 第二步：获取用户详细信息
        user_detail = wecom_api.get_user_detail(userid)
        log.info(f"获取到用户详细信息: {user_detail}")
        
        # 第三步：获取用户敏感信息（手机号）
        phone_number = None
        if user_ticket:
            try:
                user_sensitive = wecom_api.get_user_sensitive_info(user_ticket)
                log.info(f"获取到用户敏感信息: {user_sensitive}")
                phone_number = user_sensitive.get("mobile")
            except Exception as e:
                log.warning(f"获取用户敏感信息失败: {e}")
        
        # 如果无法获取敏感信息，尝试从基本信息中获取手机号
        if not phone_number:
            phone_number = user_detail.get("mobile")
        
        if not phone_number:
            raise HTTPException(
                status_code=400,
                detail="无法获取用户手机号，请确保在企业微信中设置了手机号，或者在应用中启用敏感信息授权"
            )
        
        # 第四步：根据手机号匹配系统用户
        user = Users.get_user_by_phone_number(phone_number)
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"手机号 {phone_number} 未在系统中注册，请联系管理员"
            )
        
        # 第五步：生成token并自动登录
        token = create_token(
            data={"id": user.id},
            expires_delta=None  # 使用默认过期时间
        )
        
        # 设置cookie
        expires_at = int(time.time()) + (7 * 24 * 60 * 60)  # 7天过期
        response.set_cookie(
            key="token",
            value=token,
            expires=datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc),
            httponly=True,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
            path="/",  # 确保cookie在整个域名下都有效
        )
        
        # 更新用户最后活跃时间
        Users.update_user_last_active_by_id(user.id)
        
        log.info(f"用户 {user.name} ({phone_number}) 通过企业微信成功登录")
        
        # 使用特殊路径重定向，避免前端路由拦截
        redirect_url = f"/api/v1/auths/wecom/success?token={token}"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"企业微信登录过程中发生错误: {e}")
        raise HTTPException(status_code=500, detail="登录失败，请稍后重试")


@router.post("/auth", response_model=SessionUserResponse)
async def wecom_auth(request: Request, response: Response, form_data: WeComAuthForm):
    """通过企业微信授权码进行认证（API接口）"""
    if not ENABLE_WECOM_AUTH.value:
        raise HTTPException(status_code=400, detail="企业微信认证未启用")
    
    try:
        # 初始化企业微信API
        wecom_api = WeComAPI(WECOM_CORP_ID.value, WECOM_SECRET.value)
        
        # 获取用户信息
        user_info = wecom_api.get_user_info(form_data.code)
        userid = user_info.get("userid")
        user_ticket = user_info.get("user_ticket")
        
        if not userid:
            raise HTTPException(
                status_code=400,
                detail="无法获取用户标识，可能不是企业成员"
            )
        
        # 获取用户详细信息和手机号
        user_detail = wecom_api.get_user_detail(userid)
        
        phone_number = None
        if user_ticket:
            try:
                user_sensitive = wecom_api.get_user_sensitive_info(user_ticket)
                phone_number = user_sensitive.get("mobile")
            except:
                pass
        
        if not phone_number:
            phone_number = user_detail.get("mobile")
        
        if not phone_number:
            raise HTTPException(
                status_code=400,
                detail="无法获取用户手机号"
            )
        
        # 根据手机号匹配系统用户
        user = Users.get_user_by_phone_number(phone_number)
        if not user:
            raise HTTPException(
                status_code=400,
                detail=f"手机号 {phone_number} 未在系统中注册"
            )
        
        # 生成token
        token = create_token(data={"id": user.id})
        expires_at = int(time.time()) + (7 * 24 * 60 * 60)
        
        # 设置cookie
        response.set_cookie(
            key="token",
            value=token,
            expires=datetime.datetime.fromtimestamp(expires_at, datetime.timezone.utc),
            httponly=True,
            samesite=WEBUI_AUTH_COOKIE_SAME_SITE,
            secure=WEBUI_AUTH_COOKIE_SECURE,
            path="/",  # 确保cookie在整个域名下都有效
        )
        
        # 更新用户最后活跃时间
        Users.update_user_last_active_by_id(user.id)
        
        # 获取用户权限
        user_permissions = get_permissions(
            user.id, request.app.state.config.USER_PERMISSIONS
        )
        
        return {
            "token": token,
            "token_type": "Bearer",
            "expires_at": expires_at,
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "permissions": user_permissions,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"企业微信认证过程中发生错误: {e}")
        raise HTTPException(status_code=500, detail="认证失败，请稍后重试")


@router.get("/success")
async def wecom_success(request: Request, token: str):
    """企业微信登录成功页面，用于设置localStorage并重定向"""
    
    # 验证token的有效性
    try:
        data = decode_token(token)
        if not data or "id" not in data:
            raise HTTPException(status_code=400, detail="无效的token")
    except:
        raise HTTPException(status_code=400, detail="无效的token")
    
    # 创建一个包含JavaScript代码的重定向页面，用于设置localStorage
    import json
    token_json = json.dumps(token)
    
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>登录成功 - Open WebUI</title>
        <meta charset="utf-8">
        <script>
            try {{
                console.log('企业微信登录成功，正在设置token...');
                // 使用JSON.parse确保token被正确解析
                var token = {token_json};
                localStorage.setItem('token', token);
                console.log('Token已设置到localStorage:', token.substring(0, 20) + '...');
                
                // 延迟一点时间确保localStorage设置完成
                setTimeout(function() {{
                    console.log('正在重定向到首页...');
                    window.location.href = '/';
                }}, 100);
            }} catch (error) {{
                console.error('设置token时发生错误:', error);
                // 如果出错，仍然尝试重定向
                alert('登录成功，但无法自动跳转，请手动刷新页面');
                window.location.href = '/';
            }}
        </script>
    </head>
    <body>
        <div style="text-align: center; margin-top: 50px; font-family: Arial, sans-serif;">
            <h2>🎉 企业微信登录成功</h2>
            <p>正在跳转到主页...</p>
            <p style="color: #666; font-size: 14px;">如果页面没有自动跳转，请<a href="/">点击这里</a></p>
        </div>
    </body>
    </html>
    '''
    
    return HTMLResponse(content=html_content)


@router.get("/config")
async def get_wecom_config():
    """获取企业微信配置信息（去敏感信息）"""
    return {
        "enabled": ENABLE_WECOM_AUTH.value,
        "corp_id": WECOM_CORP_ID.value,
        "agent_id": WECOM_AGENT_ID.value,
        "redirect_uri": WECOM_REDIRECT_URI.value,
        # 不返回secret等敏感信息
    } 