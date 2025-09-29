from flask_mail import Message
from config.config_mail import mail
from models import DerechoFijoModel
from flask import jsonify
import os


def enviar_mail(destinatario: str, asunto: str, html: str, adjuntos: list = None):
    msg = Message(asunto, recipients=[destinatario])
    msg.html = html
    # adjuntos = [(filename, mimetype, bytes_content), ...]
    for adj in adjuntos or []:
        filename, mimetype, content = adj
        msg.attach(filename=filename, content_type=mimetype, data=content)
    mail.send(msg)



def enviar_comprobante_pago_por_mail(uuid_derecho_fijo, payment_method, payment_id):
    try:

        # Destinatario (por ahora fijo o tomado del form si lo mandás)
        derecho_fijo = DerechoFijoModel.query.filter_by(uuid=uuid_derecho_fijo).first()

        if not derecho_fijo:
            return jsonify({"error al enviar mail": "Formulario no encontrado"}), 404
        
        destinatario = derecho_fijo.email
    
        # Link directo para descargar el comprobante (usa el backend actual)
        backend_url = os.environ.get('BACKEND_URL', 'http://localhost:5000')
        download_link = f"{backend_url}/api/forms/download_receipt?derecho_fijo_uuid={derecho_fijo.uuid}"
        # Asunto
        asunto = f"Pago registrado para el Derecho Fijo del expediente {derecho_fijo.juicio_n}"

        
        html = f"""
        <div style="font-family:Arial,Helvetica,sans-serif; color:#222;">
        <h2>Pago registrado</h2>
        <p>Se registró el pago del Derecho Fijo del expediente <b>{derecho_fijo.juicio_n}</b>.</p>
        <ul>
            <li>Carátula: {derecho_fijo.caratula or '-'}</li>
            <li>Juzgado: {derecho_fijo.juzgado or '-'}</li>
            <li>Total depositado: <b>${derecho_fijo.total_depositado}</b></li>
            <li>Método: {payment_method}</li>
            <li>ID de pago: {payment_id}</li>
        </ul>
        <p>Podés descargar el comprobante desde este enlace:</p>
        <p><a href="{download_link}" target="_blank">{download_link}</a></p>
        <hr/>
        <p style="font-size:12px;color:#666;">Colegio Público de Abogados y Procuradores – Segunda Circunscripción (Mendoza)</p>
        </div>
        """

        enviar_mail(destinatario, asunto, html)
    
    except Exception as ex:
        print("⚠️ Error preparando el correo", ex)
        return None