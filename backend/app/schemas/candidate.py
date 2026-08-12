"""Candidate/account API contracts.

The compatibility table is still named ``candidate`` in the persistence
layer, but the public identity contract is an email-first platform account.
Keep these schemas deliberately strict: accepting one of the removed roster
fields here would make it possible for clients to bypass the registration
flow even after the migration has removed those columns.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    TypeAdapter,
    field_validator,
)

from app.schemas.common import ORMModel

_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def normalize_email(value: object) -> str:
    """Return the canonical email key used throughout the application.

    Only whitespace trimming and case folding are intentional.  Provider
    aliases (plus-addresses, dots, etc.) are not rewritten because doing so
    would silently merge distinct mailboxes.
    """

    if not isinstance(value, str):
        raise ValueError("请输入有效邮箱")
    normalized = value.strip().lower()
    if not normalized or len(normalized) > 255:
        raise ValueError("请输入有效邮箱")
    try:
        validated = _EMAIL_ADAPTER.validate_python(normalized)
    except ValueError:
        raise ValueError("请输入有效邮箱") from None
    return str(validated).strip().lower()


CandidateEmail = Annotated[EmailStr, Field(max_length=255)]
CandidateOtp = Annotated[str, Field(pattern=r"^\d{6}$")]
CandidateDisplayName = Annotated[str, Field(max_length=100)]
AccountStatus = Literal["pending", "active", "inactive"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CandidateLoginRequest(StrictModel):
    email: CandidateEmail

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str:
        return normalize_email(value)  # type: ignore[arg-type]


class CandidateLoginChallengeResponse(BaseModel):
    challenge_id: int
    expires_at: datetime
    resend_available_at: datetime


class CandidateLoginVerifyRequest(StrictModel):
    challenge_id: int = Field(gt=0)
    otp: CandidateOtp

    @field_validator("otp", mode="before")
    @classmethod
    def _trim_otp(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CandidateRead(ORMModel):
    """Public account representation.

    ``name`` remains accepted as an ORM input alias while ``display_name`` is
    the only serialized field.  This lets the compatibility model retain its
    existing physical column during the additive migration without exposing
    legacy personnel identity fields in the API.
    """

    id: int
    email: CandidateEmail
    display_name: CandidateDisplayName | None = Field(
        default=None,
        validation_alias=AliasChoices("display_name", "name"),
    )
    status: AccountStatus

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str:
        return normalize_email(value)  # type: ignore[arg-type]


class AccountProfileRead(CandidateRead):
    pass


class AuthenticatedCandidateLoginResponse(StrictModel):
    outcome: Literal["authenticated"]
    account: CandidateRead
    token: str
    token_expires_at: datetime


class RegistrationRequiredResponse(StrictModel):
    outcome: Literal["registration_required"]
    registration_credential: str
    registration_expires_at: datetime
    email: CandidateEmail
    suggested_display_name: CandidateDisplayName | None = None

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str:
        return normalize_email(value)  # type: ignore[arg-type]


class AccountUnavailableResponse(StrictModel):
    outcome: Literal["account_unavailable"]
    message: str = "账号暂不可用，请联系管理员重新激活。"


CandidateLoginVerifyResponse = Annotated[
    AuthenticatedCandidateLoginResponse
    | RegistrationRequiredResponse
    | AccountUnavailableResponse,
    Field(discriminator="outcome"),
]


class RegistrationCompleteRequest(StrictModel):
    registration_credential: str = Field(min_length=1, max_length=256)
    display_name: CandidateDisplayName

    @field_validator("display_name")
    @classmethod
    def _require_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("姓名不能为空")
        return normalized


class CandidateProfileUpdate(StrictModel):
    display_name: CandidateDisplayName

    @field_validator("display_name")
    @classmethod
    def _require_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("姓名不能为空")
        return normalized


class AccountStatusUpdate(StrictModel):
    status: Literal["active", "inactive"]


class AccountAdminRead(CandidateRead):
    created_at: datetime | None = None
    updated_at: datetime | None = None
