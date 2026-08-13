"""Thin Google Gemini client used to grade the spoken parts of the HSKK exam.

Deliberately built on ``urllib`` from the standard library rather than an HTTP
package: the app is shipped as a PyInstaller ``.exe`` and one JSON POST does not
justify another bundled dependency.

The credential is read from the environment only (see ``backend.settings``) and
is never logged, echoed to the client, or written into the repository.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

from backend.logging_config import get_logger
from backend.services.errors import InvalidOperationError
from backend.settings import get_settings


logger = get_logger("gemini")

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"

NOT_CONFIGURED_MESSAGE = (
    "Chưa cấu hình khoá Gemini nên không chấm điểm bằng AI được. "
    "Đặt biến môi trường GEMINI_API_KEY rồi khởi động lại máy chủ."
)


def is_configured() -> bool:
    return get_settings().gemini_configured


def _request(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.gemini_configured:
        raise InvalidOperationError(NOT_CONFIGURED_MESSAGE)

    url = f"{API_ROOT}/{settings.gemini_model}:generateContent"
    headers = {"Content-Type": "application/json"}
    if settings.gemini_uses_bearer_token:
        headers["Authorization"] = f"Bearer {settings.gemini_api_key}"
    else:
        headers["x-goog-api-key"] = settings.gemini_api_key

    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.gemini_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # The body often explains exactly what is wrong (expired token, quota,
        # unsupported model), but it can also echo the credential back, so only
        # the status and Google's short reason are surfaced.
        detail = ""
        try:
            body = json.loads(error.read().decode("utf-8"))
            detail = str(body.get("error", {}).get("message", ""))[:200]
        except Exception:  # noqa: BLE001 - diagnostics must never mask the real error
            detail = ""
        logger.warning("Gemini rejected the request: %s %s", error.code, detail)
        if error.code in {401, 403}:
            raise InvalidOperationError(
                "Khoá Gemini bị từ chối hoặc đã hết hạn. Hãy tạo khoá mới rồi cập nhật "
                "biến môi trường GEMINI_API_KEY."
            ) from error
        if error.code == 429:
            raise InvalidOperationError(
                "Gemini đang giới hạn số lượt gọi. Chờ một lát rồi chấm lại."
            ) from error
        raise InvalidOperationError(
            f"Gemini trả lỗi {error.code}. {detail}".strip()
        ) from error
    except urllib.error.URLError as error:
        logger.warning("Cannot reach Gemini: %s", error.reason)
        raise InvalidOperationError(
            "Không kết nối được tới Gemini. Kiểm tra mạng rồi thử lại."
        ) from error


def _extract_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates") or []
    if not candidates:
        # Safety filters return no candidate at all; say so instead of crashing.
        raise InvalidOperationError("Gemini không trả về kết quả cho bài nói này.")
    parts = candidates[0].get("content", {}).get("parts") or []
    return "".join(part.get("text", "") for part in parts).strip()


def _parse_json_object(text: str) -> dict[str, Any]:
    """Read the model's JSON answer, tolerating a ```json fence around it."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise InvalidOperationError("Gemini trả về dữ liệu không đọc được.") from None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            raise InvalidOperationError("Gemini trả về dữ liệu không đọc được.") from None
    if not isinstance(parsed, dict):
        raise InvalidOperationError("Gemini trả về dữ liệu không đúng định dạng.")
    return parsed


def generate_json(
    *,
    system_instruction: str,
    prompt: str,
    audio_base64: str | None = None,
    audio_mime_type: str = "audio/wav",
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Ask Gemini for a JSON object, optionally about an attached audio clip."""
    parts: list[dict[str, Any]] = [{"text": prompt}]
    if audio_base64:
        parts.append({"inline_data": {"mime_type": audio_mime_type, "data": audio_base64}})

    payload: dict[str, Any] = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            # Asking for JSON explicitly removes most of the parsing guesswork;
            # `_parse_json_object` stays as the belt-and-braces fallback.
            "responseMimeType": "application/json",
        },
    }
    return _parse_json_object(_extract_text(_request(payload)))
