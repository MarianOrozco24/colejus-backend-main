import os, base64, hmac, hashlib, time, threading
from datetime import datetime, timezone
from flask import request, abort, g

# Cache anti-replay en memoria (nonce -> expiry)
_NONCE_CACHE = {}
_NONCE_LOCK = threading.Lock()

def _now_ts() -> int:
    return int(time.time())

def _parse_ts(ts_val: str) -> int:
    """
    Acepta epoch (int/str) o ISO8601. Devuelve epoch (int).
    """
    if ts_val is None:
        raise ValueError("Falta X-TIMESTAMP")
    ts_val = str(ts_val).strip()
    # Epoch?
    if ts_val.isdigit():
        return int(ts_val)
    # ISO8601?
    try:
        dt = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
        return int(dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp())
    except Exception:
        raise ValueError("Formato inválido de X-TIMESTAMP")

def _constant_time_equals(a: str, b: str) -> bool:
    try:
        return hmac.compare_digest(a, b)
    except Exception:
        return False

def _sign_raw_body(secret: str, raw: bytes) -> str:
    """
    Firma HMAC-SHA256 del body crudo. Devuelve Base64 (string).
    """
    dig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).digest()
    return base64.b64encode(dig).decode("utf-8")

def _check_ip_allowlist():
    allowlist = os.getenv("BCM_IP_ALLOWLIST", "").strip()
    if not allowlist:
        return  # desactivado
    allowed = {ip.strip() for ip in allowlist.split(",") if ip.strip()}
    # Usa proxy-aware cabeceras si tenés reverse proxy:
    real_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
    # X-Forwarded-For puede traer lista, tomamos el primer IP
    real_ip = real_ip.split(",")[0].strip()
    if real_ip not in allowed:
        abort(403, description="IP no permitida")

def _check_content_type_and_size(max_len=100_000):
    ctype = (request.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if ctype != "application/json":
        abort(415, description="Content-Type inválido (se requiere application/json)")
    # Límite de tamaño
    cl = request.content_length
    if cl is not None and cl > max_len:
        abort(413, description="Payload demasiado grande")

def verify_bcm_webhook_security():
    """
    Valida:
      - IP allowlist (opcional)
      - Content-Type y tamaño
      - API-KEY, X-SIGNATURE, X-TIMESTAMP (ventana), X-NONCE (anti-replay)
      - Firma HMAC del body crudo
    Lanza abort(4xx) en caso de falla.
    """
    _check_ip_allowlist()
    _check_content_type_and_size()

    api_key_hdr = request.headers.get("API-KEY")
    sig_hdr     = request.headers.get("X-SIGNATURE")
    ts_hdr      = request.headers.get("X-TIMESTAMP")
    nonce_hdr   = request.headers.get("X-NONCE")  # recomendado

    api_key_env   = os.getenv("BOLSA_API_KEY")
    secret_env    = os.getenv("BOLSA_SECRET")
    max_skew_secs = int(os.getenv("BOLSA_WEBHOOK_MAX_SKEW", "300"))

    if not api_key_env or not secret_env:
        abort(500, description="Servidor mal configurado (falta API_KEY o SECRET)")

    if not api_key_hdr or not sig_hdr or not ts_hdr or not nonce_hdr:
        abort(401, description="Headers requeridos ausentes (API-KEY, X-SIGNATURE, X-TIMESTAMP, X-NONCE)")

    if api_key_hdr != api_key_env:
        abort(401, description="API-KEY inválida")

    # Validar timestamp (anti-replay por tiempo)
    ts = _parse_ts(ts_hdr)
    now = _now_ts()
    if abs(now - ts) > max_skew_secs:
        abort(401, description="X-TIMESTAMP fuera de ventana")

    # Validar nonce (anti-replay por unicidad)
    with _NONCE_LOCK:
        # limpiar expirados ocasionalmente
        for k, exp in list(_NONCE_CACHE.items()):
            if exp < now:
                _NONCE_CACHE.pop(k, None)
        # registrar nuevo nonce
        if nonce_hdr in _NONCE_CACHE:
            abort(401, description="Replay detectado (nonce repetido)")
        _NONCE_CACHE[nonce_hdr] = now + max_skew_secs  # mismo TTL que la ventana

     # ✅ cache=True para que Flask guarde el body y se pueda leer de nuevo
    raw = request.get_data(cache=True, as_text=False)

    # ... calcular expected_sig sobre `raw` como antes ...
    expected_sig = _sign_raw_body(secret_env, raw)

    # Guardamos para consumirlo después sin re-parsear
    g.bcm_raw_body = raw

    if not _constant_time_equals(sig_hdr, expected_sig):
        abort(401, description="X-SIGNATURE inválida")
