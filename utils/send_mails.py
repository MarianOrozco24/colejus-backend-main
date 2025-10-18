from flask_mail import Message
from flask import jsonify,  current_app
from models.derecho_fijo import DerechoFijoModel
from config.config_mail import mail
import os, traceback


def _dump_mail_config():
    cfg = {k: current_app.config.get(k) for k in (
        "MAIL_SERVER","MAIL_PORT","MAIL_USE_TLS","MAIL_USE_SSL",
        "MAIL_USERNAME","MAIL_DEFAULT_SENDER", "MAIL_PASSWORD"
    )}
    print("[MAIL CONFIG]", cfg)

def enviar_mail(destinatario: str, asunto: str, html: str, adjuntos: list = None):


    try:
        msg = Message(
            subject=asunto,
            recipients=[destinatario],
            sender=('Colegio Público de Abogados', 'payments@colejus.com.ar')
        )
        msg.html = html

        # Adjuntos si hay (lista de tuplas: [(filename, mimetype, bytes_content), ...])
        for adj in adjuntos or []:
            filename, mimetype, content = adj
            msg.attach(filename=filename, content_type=mimetype, data=content)

        mail.send(msg)
        print(f"✅ Correo enviado correctamente a {destinatario}")
        return True
    

    except Exception as e:
        print(f"⚠️ Error al enviar correo a {destinatario}: {e}")
        traceback.print_exc()
        return False
    



def enviar_comprobante_pago_por_mail(uuid_derecho_fijo, payment_method, payment_id):
    try:
        derecho_fijo = DerechoFijoModel.query.filter_by(uuid=uuid_derecho_fijo).first()

        if not derecho_fijo:
            return jsonify({"error": "Formulario no encontrado"}), 404

        destinatario = derecho_fijo.email

        if not destinatario:
            return jsonify({"error": "El formulario no contiene un email válido"}), 404

        backend_url = os.environ.get('BACKEND_URL', 'http://localhost:5000')
        download_link = f"{backend_url}/api/forms/download_receipt?derecho_fijo_uuid={derecho_fijo.uuid}"

        asunto = f"Pago registrado – Expediente {derecho_fijo.juicio_n or ''}"

        html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f7fa;padding:30px 0;">
        <tr>
            <td align="center">
            <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border-radius:10px;box-shadow:0 4px 10px rgba(0,0,0,0.05);font-family:Arial,Helvetica,sans-serif;color:#333;">
                <tr>
                <td style="background:#0b3d91;padding:20px 30px;border-radius:10px 10px 0 0;color:#fff;text-align:center;">
                    <h1 style="margin:0;font-size:22px;">Pago Registrado</h1>
                </td>
                </tr>
                <tr>
                <td style="padding:30px;">
                    <p style="font-size:16px;margin:0 0 15px 0;">Estimado/a cliente,</p>
                    <p style="font-size:15px;margin:0 0 20px 0;">
                    Se ha registrado exitosamente el pago del Derecho Fijo correspondiente al expediente 
                    <strong>{derecho_fijo.juicio_n or ''}</strong>.
                    </p>

                    <table cellpadding="6" cellspacing="0" border="0" width="100%" style="background:#f9fafc;border:1px solid #e2e6ef;border-radius:8px;margin-bottom:25px;">
                    <tr>
                        <td width="40%" style="font-weight:bold;">Carátula:</td>
                        <td>{derecho_fijo.caratula or '-'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:bold;">Juzgado:</td>
                        <td>{derecho_fijo.juzgado or '-'}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:bold;">Total depositado:</td>
                        <td>${derecho_fijo.total_depositado or 0}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:bold;">Método:</td>
                        <td>{payment_method}</td>
                    </tr>
                    <tr>
                        <td style="font-weight:bold;">ID de pago:</td>
                        <td>{payment_id}</td>
                    </tr>
                    </table>

                    <p style="font-size:15px;margin-bottom:25px;">Podés descargar el comprobante desde el siguiente enlace:</p>
                    <p style="text-align:center;">
                    <a href="{download_link}" target="_blank"
                        style="display:inline-block;background:#0b3d91;color:#fff;text-decoration:none;
                                padding:12px 25px;border-radius:6px;font-weight:bold;">
                        Descargar Comprobante
                    </a>
                    </p>

                    <hr style="border:none;border-top:1px solid #eee;margin:30px 0;" />

                    <p style="font-size:12px;color:#666;text-align:center;line-height:1.4;">
                    Colegio Público de Abogados y Procuradores<br/>
                    Segunda Circunscripción – Mendoza<br/>
                    <a href="https://colejus.com.ar" style="color:#0b3d91;text-decoration:none;">www.colejus.com.ar</a>
                    </p>
                </td>
                </tr>
            </table>
            </td>
        </tr>
        </table>
        """


        enviar_mail(destinatario, asunto, html)
        return jsonify({"mensaje": f"Correo enviado correctamente a {destinatario}"}), 200

    except Exception as ex:
        print("⚠️ Error preparando o enviando el correo:", ex)
        return jsonify({"error": str(ex)}), 500
