import os
from flask_mail import Mail

mail = Mail()

def _boolenv(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1","true","yes","on")

def init_mail(app):
    server   = os.getenv('MAIL_SERVER', '').strip()
    port     = int(os.getenv('MAIL_PORT', '587').strip())
    use_tls  = _boolenv('MAIL_USE_TLS', True)
    use_ssl  = _boolenv('MAIL_USE_SSL', False)
    user     = (os.getenv('MAIL_USERNAME') or '').strip()
    pwd      = (os.getenv('MAIL_PASSWORD') or '').strip()
    sender   = (os.getenv('MAIL_FROM') or 'payments@colejus.com.ar').strip()

    # Validaciones claras para evitar 535 silencioso
    if not server:
        raise RuntimeError("MAIL_SERVER vacío.")
    if not user or '@' not in user:
        raise RuntimeError("MAIL_USERNAME vacío o inválido. Debe ser el SMTP Username completo.")
    if not pwd:
        raise RuntimeError("MAIL_PASSWORD vacío.")

    # Coherencia puerto/seguridad
    if port == 587 and (not use_tls or use_ssl):
        raise RuntimeError("Para puerto 587: MAIL_USE_TLS=True y MAIL_USE_SSL=False.")
    if port == 465 and (use_tls or not use_ssl):
        raise RuntimeError("Para puerto 465: MAIL_USE_TLS=False y MAIL_USE_SSL=True.")

    app.config.update(
        MAIL_SERVER=server,
        MAIL_PORT=port,
        MAIL_USE_TLS=use_tls,
        MAIL_USE_SSL=use_ssl,
        MAIL_USERNAME=user,
        MAIL_PASSWORD=pwd,
        MAIL_DEFAULT_SENDER=('Colegio Público de Abogados', sender),
        MAIL_SUPPRESS_SENDING=False,   # dejar False en prod
    )

    # Log simple (sin password)
    app.logger.info(
        f"[MAIL] server={server} port={port} tls={use_tls} ssl={use_ssl} user={user!r} sender={sender!r}"
    )

    mail.init_app(app)
    return mail  # <— devolvé el objeto correctamente
