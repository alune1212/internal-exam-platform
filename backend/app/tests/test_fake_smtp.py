from app.ops.fake_smtp import MESSAGES, _latest_message


def test_latest_message_can_select_otp_after_an_invitation() -> None:
    MESSAGES.clear()
    MESSAGES.extend(
        [
            {
                "to": "person@example.com",
                "subject": "考试平台登录验证码",
                "otp": "246810",
            },
            {
                "to": "person@example.com",
                "subject": "考试邀请",
                "otp": "",
            },
        ]
    )

    assert _latest_message("person@example.com") == MESSAGES[-1]
    assert _latest_message("person@example.com", "otp") == MESSAGES[0]
    assert _latest_message("missing@example.com", "otp") is None
    MESSAGES.clear()
