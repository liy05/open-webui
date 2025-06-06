import logging
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_db
from open_webui.models.users import UserModel, Users
from open_webui.env import SRC_LOG_LEVELS
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, String, Text
from open_webui.utils.auth import verify_password
from open_webui.utils.sms_service import verify_code

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# DB MODEL
####################


class Auth(Base):
    __tablename__ = "auth"

    id = Column(String, primary_key=True)
    email = Column(String)
    password = Column(Text)
    active = Column(Boolean)


####################
# API MODELS
####################


class AuthModel(BaseModel):
    id: str
    email: str
    password: str
    active: bool


class Token(BaseModel):
    token: str
    token_type: str


class ApiKey(BaseModel):
    api_key: str


class SigninForm(BaseModel):
    email: str
    password: str


class PhoneLoginForm(BaseModel):
    phone_number: str
    verification_code: str


class SendSmsCodeForm(BaseModel):
    phone_number: str


class SignupForm(BaseModel):
    name: str
    email: str
    password: str
    profile_image_url: Optional[str] = "/user.png"


class LdapForm(BaseModel):
    user: str
    password: str


class SigninResponse(BaseModel):
    token: str
    token_type: str
    id: str
    email: str
    name: str
    role: str
    profile_image_url: str
    phone_number: Optional[str] = None


class AddUserForm(BaseModel):
    name: str
    email: str
    password: str
    role: str = "pending"
    profile_image_url: Optional[str] = None
    phone_number: Optional[str] = None


class UpdateProfileForm(BaseModel):
    name: str
    profile_image_url: str
    phone_number: Optional[str] = None


class UpdatePasswordForm(BaseModel):
    password: str
    new_password: str


class WeComAuthForm(BaseModel):
    code: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    profile_image_url: str
    phone_number: Optional[str] = None


####################
# AUTH CLASS
####################


class AuthsTable:
    def insert_new_auth(
        self,
        email: str,
        password: str,
        name: str,
        profile_image_url: str = "/user.png",
        role: str = "pending",
        oauth_sub: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> Optional[UserModel]:
        with get_db() as db:
            log.info("insert_new_auth")

            id = str(uuid.uuid4())

            auth = AuthModel(
                **{"id": id, "email": email, "password": password, "active": True}
            )
            result = Auth(**auth.model_dump())
            db.add(result)

            user = Users.insert_new_user(
                id, name, email, profile_image_url, role, oauth_sub, phone_number
            )

            db.commit()
            db.refresh(result)

            if result and user:
                return user
            else:
                return None

    def authenticate_user(self, email: str, password: str) -> Optional[UserModel]:
        log.info(f"authenticate_user: {email}")
        try:
            with get_db() as db:
                auth = db.query(Auth).filter_by(email=email, active=True).first()
                if auth:
                    if verify_password(password, auth.password):
                        user = Users.get_user_by_id(auth.id)
                        return user
                    else:
                        return None
                else:
                    return None
        except Exception:
            return None

    def authenticate_user_by_phone_code(self, phone_number: str, code: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_phone_code: {phone_number}")
        try:
            # 验证短信验证码
            if verify_code(phone_number, code):
                # 根据手机号获取用户
                user = Users.get_user_by_phone_number(phone_number)
                if user:
                    return user
            return None
        except Exception as e:
            log.error(f"Phone verification error: {str(e)}")
            return None

    def authenticate_user_by_api_key(self, api_key: str) -> Optional[UserModel]:
        log.info(f"authenticate_user_by_api_key: {api_key}")
        # if no api_key, return None
        if not api_key:
            return None

        try:
            user = Users.get_user_by_api_key(api_key)
            return user if user else None
        except Exception:
            return False

    def authenticate_user_by_trusted_header(self, email: str) -> Optional[UserModel]:
        try:
            user = Users.get_user_by_email(email)
            if user:
                return user
            else:
                return None
        except Exception:
            return None

    def update_user_password_by_id(self, id: str, new_password: str) -> bool:
        try:
            with get_db() as db:
                result = (
                    db.query(Auth).filter_by(id=id).update({"password": new_password})
                )
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def update_email_by_id(self, id: str, email: str) -> bool:
        try:
            with get_db() as db:
                result = db.query(Auth).filter_by(id=id).update({"email": email})
                db.commit()
                return True if result == 1 else False
        except Exception:
            return False

    def delete_auth_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                # Delete User
                result = Users.delete_user_by_id(id)

                if result:
                    db.query(Auth).filter_by(id=id).delete()
                    db.commit()

                    return True
                else:
                    return False
        except Exception:
            return False


Auths = AuthsTable()
