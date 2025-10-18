from datetime import datetime, timedelta
from flask import Blueprint, app, request, jsonify, send_file, g, url_for
from sqlalchemy import and_, or_
from config.config import db
from models import DerechoFijoModel, RateModel, ReceiptModel, PriceDerechoFijo
from utils.decorators import token_required, access_required
from utils.send_mails import enviar_comprobante_pago_por_mail, enviar_mail
from flask_jwt_extended import jwt_required
from utils.errors import ValidationError, register_in_txt
from config.config_mp import get_mp_sdk
import qrcode
import base64
from sqlalchemy import desc
from utils.seguridad_bcm import verify_bcm_webhook_security
from flask import current_app
from flask_mail import Message
from config.config_mail import mail

from io import BytesIO
from typing import List, Dict
import math
from models.interest import InterestPeriod
from models.rate import RateType
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from io import BytesIO
import logging
from utils.bot import enviar_alerta
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
import os, base64, hmac, hashlib, requests
from datetime import datetime
from io import BytesIO
import qrcode
import hmac, hashlib, json

from reportlab.lib.utils import ImageReader


forms_bp = Blueprint('forms_bp', __name__)

BOLSA_BASE_URL = os.getenv("BOLSA_BASE_URL", "")     
BOLSA_API_KEY  = os.getenv("BOLSA_API_KEY", "")
BOLSA_CLIENT_ID = os.getenv("BOLSA_CLIENT_ID", "")
BOLSA_SECRET   = os.getenv("BOLSA_SECRET", "")

def _make_qr_png_bytes(qr_payload, box_size=8, border=2, err=qrcode.constants.ERROR_CORRECT_M):
    qr = qrcode.QRCode(version=None, error_correction=err, box_size=box_size, border=border)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return buf

def _bolsa_signature():
    if not (BOLSA_CLIENT_ID and BOLSA_SECRET):
        return None
    
    digest = hmac.new(BOLSA_SECRET.encode(), BOLSA_CLIENT_ID.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()

def call_bolsa_create_boleta(derecho_fijo):

    print("🔍 Llamando a Bolsa API para crear boleta...")

    """Si la Bolsa te da API, usala; si no, devolvé None y armamos local."""
    if not BOLSA_BASE_URL or not BOLSA_API_KEY or not _bolsa_signature():
        print("Bolsa base url: ",BOLSA_BASE_URL)
        print("Bolsa API key: ",BOLSA_API_KEY)
        print("Bolsa signature: ",_bolsa_signature())
        
        print("⚠️ Bolsa API no disponible, usando formato local.")
        return None
    
    try:
        url = f"{BOLSA_BASE_URL}/boletas"
        
        payload = {
            "external_id": derecho_fijo.uuid,
            "amount": float(derecho_fijo.total_depositado or 0),
            "due_date": (getattr(derecho_fijo, "fecha", None) or datetime.utcnow()).strftime("%Y-%m-%d"),
            "case_number": derecho_fijo.juicio_n or "",
            "court": derecho_fijo.juzgado or "",
            "party": derecho_fijo.parte or "",
        }
        headers = {
            "API-KEY": BOLSA_API_KEY,
            "X-SIGNATURE": _bolsa_signature(),
            "Content-Type": "application/json",
        }
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        # normalizá claves según defina la Bolsa
        return data.get("barcode") or data.get("bar_code"), data.get("qr_payload") or data.get("qr")
    except Exception as e:
        print("⚠️ Bolsa API no disponible, usando formato local:", e)
        return None

def get_bolsa_identifiers(derecho_fijo):
    # 1) Intentar API oficial
    res = call_bolsa_create_boleta(derecho_fijo)
    
    if res:
        return res[0], res[1]
    
    # 2) Fallback local (ajustá a la especificación final)
    monto = str(getattr(derecho_fijo, "total_depositado", "0"))
    venc  = getattr(derecho_fijo, "fecha", None)
    venc_yyyymmdd = venc.strftime("%Y%m%d") if venc else datetime.utcnow().strftime("%Y%m%d")
    
    barcode_string = f"CBAMZA|{derecho_fijo.uuid[:12]}|{monto}|{venc_yyyymmdd}|1" # Pagina de redireccion a la hora de escanear qr
    qr_payload = barcode_string

    return barcode_string, qr_payload




def build_canonical_string(payload: dict) -> str:
    # Ordena por clave, sin espacios para que sea determinístico
    return json.dumps(payload, ensure_ascii=False, separators=(',', ':'), sort_keys=True)

def generar_firma(payload: dict, secret: str) -> str:
    msg = build_canonical_string(payload).encode("utf-8")
    key = secret.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()

def bcm_signature(client_id: str, secret: str) -> str:
    dig = hmac.new(secret.encode("utf-8"), client_id.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(dig).decode("utf-8")

def _strip_prefix(b64: str) -> str:
    return b64.split("base64,", 1)[-1].replace("\n", "").replace(" ", "")



def _extract_qr_b64(bcm_json: dict) -> str | None:
    # 1) esquema anidado típico: data.qrs[].qr_image_base64
    qrs = (bcm_json or {}).get("data", {}).get("qrs", [])
    # primero el OK, si existe
    for q in qrs:
        if (q.get("status", "").upper() == "OK") and q.get("qr_image_base64"):
            return _strip_prefix(q["qr_image_base64"])
    # luego cualquier QR que traiga imagen
    for q in qrs:
        if q.get("qr_image_base64"):
            return _strip_prefix(q["qr_image_base64"])
    # 2) fallbacks por si cambian nombres (poco probable)
    alt = (bcm_json.get("qr_image_base64")
           or bcm_json.get("qr_code_base64")
           or bcm_json.get("qrImageBase64")
           or bcm_json.get("qrBase64"))
    return _strip_prefix(alt) if alt else None
        


def obtencion_codigo_qr(preference_data: dict, api_key: str, secret: str) -> dict:
    """
    Devuelve dict con:
      - qr_image_b64: str  (PNG en base64)  ó
      - qr_url: str        (si la API devuelve URL)
      - raw: dict          (respuesta completa por si querés loggear)
    """
    # Agregamos la firma al body
    signed_payload = dict(preference_data)  # copia
    signed_payload["firma"] = generar_firma(preference_data, secret)

    headers = {
        "API-KEY": BOLSA_API_KEY,
        "X-SIGNATURE": bcm_signature(BOLSA_CLIENT_ID, BOLSA_SECRET),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    resp = requests.post(
        BOLSA_BASE_URL,
        headers=headers,
        json=preference_data,  
        timeout=20,
    )

    # Manejo explícito de status
    if resp.status_code == 200:
        data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {}
        qr_b64 = _extract_qr_b64(data)
        return {"ok": True, "qr_image_base64": qr_b64, "raw": data, "status_code": resp.status_code}    

    if resp.status_code == 401:
        raise ValueError("BCM: Unauthorized (401). Revisá BOLSA_API_KEY.")
    if resp.status_code == 403:
        raise ValueError("BCM: Forbidden (403). ¿IP permitida? ¿Rol?")
    if resp.status_code >= 500:
        raise ValueError(f"BCM: Error {resp.status_code} en el servidor. {resp.text}")

    # Para cualquier otro estado, devolvemos detalle:
    try:
        err = resp.json()
    except Exception:
        err = {"text": resp.text}
    raise ValueError(f"BCM: respuesta inesperada {resp.status_code}: {err}")

@forms_bp.route('/forms/derecho_fijo_qr_bcm', methods=['POST'])
def generar_qr_bcm():

    print("📨 Se escogió pago con QR en BCM")
    data = request.json or {}

    try:
        # 1) Validamos/normalizamos inputs mínimos
        required = ["total_depositado", "caratula", "fecha_inicio", "juicio_n", "lugar", "fecha", "tasa_justicia", "parte", "juzgado"]
        faltan = [k for k in required if not data.get(k)]
        if faltan:
            return jsonify({"error": f"Faltan campos: {', '.join(faltan)}"}), 400

        # Monto como float y formateo a string si la API lo requiere
        amount = float(str(data["total_depositado"]).replace(",", "."))

        # Fecha (ISO). Ajustá al formato exacto que pida BCM si fuese necesario.
        # p.ej. 'YYYY-MM-DD' o 'YYYY-MM-DDTHH:MM:SS'
        due = data["fecha_inicio"]  # asumo viene en ISO correcto desde el front

        # 2) Creamos DerechoFijo
        try:
            new_derecho_fijo = DerechoFijoModel.from_json(data)
            db.session.add(new_derecho_fijo)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Error al insertar datos en DB", e)
            return jsonify({"error": "No se pudo registrar sel derecho fijo"}), 500

        # 3) Armamos payload para BCM
        payment_id = ''.join(filter(str.isdigit, str(uuid.uuid4())))[:10]
        preference_data = {
            "amount": f"{amount:.2f}",         
            "description": data["caratula"],
            "transactionId": str(new_derecho_fijo.uuid),
            "due": due,
            "codigoCliente": payment_id,
            "referencia": data.get("referencia"),  
        }
        # 4) Llamada firmada a BCM
        qr_res = obtencion_codigo_qr(preference_data, BOLSA_API_KEY, BOLSA_SECRET)

        # 5) Guardamos recibo en "Pendiente"
        try:
            save_receipt_to_db(
                db.session,
                derecho_fijo=new_derecho_fijo,
                payment_id=payment_id,  # Generamos un payment_id único
                status="Pendiente",
                payment_method="QR BCM"
            )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("Error guardando recibo", e)

    
        # en tu endpoint, luego del requests.post(...)
        qr_b64 = qr_res.get("qr_image_base64")
        return jsonify({
            "ok": True,
            "payment_method": "QR BCM",
            "uuid": str(new_derecho_fijo.uuid),
            "payment_id" : payment_id,
            "qr_image_base64": qr_b64,   # <— SIEMPRE esta clave

        }), 200
     
    except ValidationError as e:
        print("Error de validación:", e)
        enviar_alerta(f"❌ Error de validación en /forms/qr_bcm: {e}")
        register_in_txt(f"Error de validación en /forms/qr_bcm: {e}", "logs_bcm.txt")
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        print("Excepción en /forms/qr_bcm:", e)
        enviar_alerta(f"❌ Excepción en /forms/qr_bcm: {e}",)
        register_in_txt(f"Excepción en /forms/qr_bcm: {e}", "logs_bcm.txt")
        db.session.rollback()
        return jsonify({"error": "Error interno"}), 500
    

    

@forms_bp.route('forms/bcm/bar-code', methods=['POST'])
def generar_boleta_bolsa():
    try:
        data = request.json

      
        nuevo_df = DerechoFijoModel.from_json(data)
        db.session.add(nuevo_df)
        db.session.commit()

        # 📌 Generar código de barras temporal (luego se usará el definitivo)
        # Este será reemplazado por el valor real que nos indique la Bolsa
        codigo_barra = f"COD-{nuevo_df.uuid}_{nuevo_df.juicio_n}_{nuevo_df.total_depositado}"

        # Codigo de barra de la bolsa
        # codigo_barra, qr_payload = get_bolsa_identifiers(nuevo_df)
        print(codigo_barra)

        # 📄 Generar PDF con código de barras
        pdf_buffer = generar_boleta_pdf_con_estilo(nuevo_df, codigo_barra)

        # Guardar recibo en estado "Pendiente"
        save_receipt_to_db(
            db.session, 
            derecho_fijo=nuevo_df, 
            payment_id=codigo_barra,
            status="Pendiente", 
            payment_method="Boleta Bolsa de Comercio"
        )

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"boleta_{nuevo_df.juicio_n}.pdf",
            mimetype="application/pdf"
        ), 200

    except Exception as e:
        db.session.rollback()
        print("❌ Error generando boleta:", e)
        enviar_alerta(f"❌ Error generando boleta: {e}")
        register_in_txt(f"Error generando boleta: {e}", "logs_bcm.txt")
        return jsonify({"error": str(e)}), 500




@forms_bp.route('/forms/derecho_fijo_qr', methods=['POST'])
def derecho_fijo_qr():
    # print("🔍 Headers:", request.headers)
    # print("🔍 Raw body:", request.data)
    print("📨 Se escogio pago con QR")
    data = request.json
    try:
        try:
            # Create and validate new DerechoFijo entry
            new_derecho_fijo = DerechoFijoModel.from_json(data)
            db.session.add(new_derecho_fijo)
            db.session.commit()
        except Exception as e:
            print("Error al insertar datos en db", e)
            return jsonify({"error": str(e)}), 500        
        

        amount = float(data['total_depositado']) # Convert total_depositado to float for Mercado Pago

        # Set up Mercado Pago preference for QR
        sdk = get_mp_sdk()
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        backend_url = os.environ.get('BACKEND_URL', 'http://localhost:5000')

        preference_data = {
            "items": [
                {
                    "title": f"Pago Derecho Fijo - {data['juicio_n']}",
                    "quantity": 1,
                    "unit_price": amount,
                    "currency_id": "ARS"
                }
            ],
            "payer": {
                "email": data.get("email", "colejus@gmail.com")
            },
            "back_urls": {
                "success": f"{frontend_url}/payment/success",
                "failure": f"{frontend_url}/payment/failure",
                "pending": f"{frontend_url}/payment/pending"
            },
            "external_reference": str(new_derecho_fijo.uuid),
            # "external_reference": "test-user-001", # 🚨 ACA: Cambiar por el UUID del derecho fijo una vez que mandemos a produccion
            "notification_url": f"{backend_url}/api/forms/webhook"
        }

        # 🚨 ACA: solo agregar "auto_return" si frontend_url es HTTPS
        if frontend_url.startswith("https://"):
            preference_data["auto_return"] = "approved"
        else:
            print("⚠️ No se incluye auto_return porque FRONTEND_URL no es HTTPS")

        # Recién acá creás la preferencia
        preference_response = sdk.preference().create(preference_data)
        # print("\n\nPreference creada:", preference_response, "\n\n")  # Debug log

        # Use init_point instead of point_of_interaction
        qr_code_url = preference_response["response"]["init_point"] 
   

        # Generate the QR code image from the URL
        qr = qrcode.make(qr_code_url)
        buffered = BytesIO()
        qr.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

        return jsonify({
            "message": "Pago creado exitosamente.",
            "qr_code_base64": qr_base64,
            "preference_id": preference_response["response"]["id"],
            "uuid": str(new_derecho_fijo.uuid)  # Add this line
        }), 201

    except ValidationError as e:
        print("Error de validacion:", e)
        enviar_alerta(f"❌ Ocurrio un error de validacion en el endpoint forms/derecho_fijo: {e}")
        register_in_txt(f"Error de validacion en forms/derecho_fijo: {e}", "logs_mp.txt")
        return jsonify({"Error:": str(e)}), 400
    except Exception as e:
        print("Error details:", e)
        enviar_alerta(f"❌ Ocurrio una excepcion en el endpoint forms/derecho_fijo {e}")
        register_in_txt(f"Excepcion en forms/derecho_fijo: {e}", "logs_mp.txt")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    


@forms_bp.route('/forms/derecho_fijo_tarjeta', methods=['POST'])
def derecho_fijo_tarjeta():
    data = request.json
    print("💳 Se escogio pago con tarjeta")
    try:
        # Create and validate new DerechoFijo entry
        new_derecho_fijo = DerechoFijoModel.from_json(data)
        db.session.add(new_derecho_fijo)
        db.session.commit()

        amount = float(data['total_depositado'])  # Convert total_depositado to float for Mercado Pago

        # Set up Mercado Pago preference for card payment
        sdk = get_mp_sdk()
        frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
        backend_url = os.environ.get('BACKEND_URL', 'http://localhost:5000')

        preference_data = {
            "items": [
                {
                    "title": f"Pago Derecho Fijo - {data['juicio_n']}",
                    "quantity": 1,
                    "unit_price": amount,
                    "currency_id": "ARS"
                }
            ],
            "payer": {
                "email": data.get("email", "colejus@colejus.com")
            },
            "back_urls": {
                "success": f"{frontend_url}/payment/success",
                "failure": f"{frontend_url}/payment/failure",
                "pending": f"{frontend_url}/payment/pending"
            },
            "external_reference": str(new_derecho_fijo.uuid),
            "notification_url": f"{backend_url}/api/forms/webhook"
        }


        # 🚨 ACA: solo agregar "auto_return" si frontend_url es HTTPS
        if frontend_url.startswith("https://"):
            preference_data["auto_return"] = "approved"
            init_point_reference = "init_point"
        else:
            print("⚠️ No se incluye auto_return porque FRONTEND_URL no es HTTPS")
            init_point_reference = "sandbox_init_point"  # fallback seguro

        # Se crea preferencia
        preference_response = sdk.preference().create(preference_data)
    
        # Use init_point for card payments
        init_point = preference_response["response"][init_point_reference]
        if not init_point:
            raise Exception("No se pudo obtener el punto de interacción para el pago con tarjeta")
        

        # Aquí puedes manejar el flujo de pago con tarjeta utilizando init_point
        return jsonify({
            "message": "Pago creado exitosamente.",
            "init_point": init_point,
            "preference_id": preference_response["response"]["id"],
            "uuid": str(new_derecho_fijo.uuid)  # Add this line
        }), 201
    

    except ValidationError as e:
        print("Error de validacion:", e)
        enviar_alerta(f"❌ Ocurrio un error de validacion en el endpoint forms/derecho_fijo_tarjeta: {e}")
        register_in_txt(f"Error de validacion en forms/derecho_fijo_tarjeta: {e}", "logs_mp.txt")
        return jsonify({"Error:": str(e)}), 400
    except Exception as e:  
        print("Error details:", e)
        enviar_alerta(f"❌ Ocurrio una excepcion en el endpoint forms/derecho_fijo_tarjeta {e}")
        register_in_txt(f"Excepcion en forms/derecho_fijo_tarjeta: {e}", "logs_mp.txt")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


## Ralizamos las importaciones de los modulos de envio de mail

@forms_bp.route("/forms/receipt-status", methods=["GET"])

def receipt_status():
    payment_id = request.args.get("payment_id", type=str)
    if not payment_id:
        return jsonify({"error": "payment_id requerido"}), 400

    r = (
        ReceiptModel.query
        .filter_by(payment_id=payment_id)
        .order_by(desc(ReceiptModel.created_at))
        .first()
    )
    if not r:
        return jsonify({"status": "Desconocido"}), 404

    is_paid = (r.status or "").lower().startswith("paga")
    download_url = None
    if is_paid:
        download_url = url_for(
            "forms_bp.download_receipt",
            derecho_fijo_uuid=r.uuid_derecho_fijo,
            _external=True
        )

    return jsonify({
        "status": r.status,                 # "Pendiente" / "Pagado"
        "receipt_number": r.receipt_number,
        "payment_method": r.payment_method, # "QR BCM"
        "download_url": download_url,
    }), 200



@forms_bp.route('/forms/webhook', methods=['POST'])
def handle_webhook():
    try:
        json_data = request.get_json()
        
        # Compatibilidad con webhook v1 (nuevo formato)
        payment_id = None
        topic = None

        if json_data:
            topic = json_data.get("type")
            data = json_data.get("data", {})
            payment_id = data.get("id")

        # Compatibilidad con simulador del panel (query string)
        if not payment_id:
            topic = request.args.get("topic") or request.args.get("type")
            payment_id = request.args.get("id") or request.args.get("data.id")

        print(f"Webhook recibido: topic={topic}, id={payment_id}")

        if topic == 'payment' and payment_id:
            sdk = get_mp_sdk()
            payment_info = sdk.payment().get(payment_id)

            if payment_info['status'] == 200:
                response_data = payment_info['response']
                status = response_data['status']
                external_reference = response_data.get('external_reference')

                print(f"Estado del pago: {status}, referencia externa: {external_reference}")

                if status == 'approved' and external_reference:
                    derecho_fijo = DerechoFijoModel.query.filter_by(uuid=external_reference).first()
                    if derecho_fijo:

                        # 🔍 Obtener tipo de pago
                        payment_type = response_data.get("payment_type_id", "qr")
                        print(f"Método de pago detectado: {payment_type}")

                        # Clasificamos tipo de pago en algo más legible
                        if payment_type == "credit_card":
                            payment_method = "Mercado Pago(TC)"
                        elif payment_type == "debit_card":
                            payment_method = "Mercado Pago(TD)"
                        else:
                            payment_method = "Mercado Pago(QR)"  # fallback

                        # Guardamos el recibo con el método correcto

                        # Colocamos prints para debugear
                        print("Procesando pago con Mercado Pago...")
                        print("uuid_derecho_fijo:", derecho_fijo.uuid, 
                              "payment_id:", payment_id,
                              "status:", status,
                              "payment_method:", payment_method)
                        
                        save_receipt_to_db(db.session, derecho_fijo, payment_id, status="Pagado", payment_method=payment_method)

                        # Envio de correo con confirmacion de pago
                        enviar_comprobante_pago_por_mail(derecho_fijo.uuid, payment_method, payment_id)
                        
                        print("✅ Recibo guardado correctamente.")

                    else:
                        print("❌ Error al consultar el pago con Mercado Pago")

        return jsonify({"message": "Webhook processed"}), 200

    except Exception as e:
        print("Error manejando webhook:", e)
        enviar_alerta(f"❌ Ocurrio un error manejando el webhook {e}")
        register_in_txt(f"Error manejando webhook: {e}", "logs_mp.txt")
        return jsonify({"error": str(e)}), 500




@forms_bp.route('/forms/payment_status/<preference_id>', methods=['GET'])
def check_payment_status(preference_id):
    try:
        print(f"Checking payment status for preference: {preference_id}")  # Debug log
        sdk = get_mp_sdk()
        
        # Get preferences to check payment
        preference = sdk.preference().get(preference_id)
        # print("Preference found:", preference)  # Debug log
        if preference:
            print("✅ Preference found")
        else:
            print("❌ Preference not found")
        
        # Search for payments with this external reference
        if preference['response'].get('external_reference'):
            search_result = sdk.payment().search({
                "external_reference": preference['response']['external_reference']
            })
            
            print("Search result:", search_result)  # Debug log
            
            if search_result.get('response', {}).get('results', []):
                payment = search_result['response']['results'][0]
                print(f"Found payment with status: {payment['status']}")
                return jsonify({
                    "status": payment['status'],
                    "payment_id": payment['id'],
                    "external_reference": preference['response']['external_reference']  # 👈 agregar esta línea
                }), 200
        
        # If no payment found, return pending
        return jsonify({
            "status": "pending"
        }), 200
        
    except Exception as e:
        traceback.print_exc()  # Print the full traceback for debugging
        print("Error checking payment status:", str(e))
        enviar_alerta(f"Error checking payment status (/forms/payment_status):  {str(e)}")
        register_in_txt(f"Error checking payment status (/forms/payment_status):  {str(e)}", "logs_mp.txt")
        return jsonify({"error": str(e)}), 500
    
@forms_bp.route('/forms/envio/mails', methods=['POST'])
def prueba_envio_mail():
    """Prueba de envío de correo. Envía un correo a la dirección especificada con el asunto y contenido HTML dados."""
    data = request.json or {}
    destinatario = data.get("destinatario", "marianorozcogs@gmail.com")
    asunto = data.get("asunto", "Prueba de envío de correo")
    html = data.get("html", "<h1>Este es un correo de prueba</h1><p>Si recibes esto, el envío funcionó correctamente.</p>")

    if enviar_mail(destinatario, asunto, html):

        return jsonify({"message": "Correo enviado correctamente"}), 200

    return jsonify({"error": "Error enviando correo"}), 500

@forms_bp.route("/forms/bcm/webhook", methods=["POST"])
def bcm_webhook_oficial():
    """
    Webhook oficial de la Bolsa.
    Requisitos (según doc): aceptar JSON y responder 200 con {"ok": true}.
    Idempotente: si ya está pagado o no se puede actualizar, igual devolvemos ok:true.
    """
    try:

        try:
            # 1) Seguridad (abort 4xx si falla)
            verify_bcm_webhook_security()
            
        except Exception as e:
            print("❌ Error de seguridad en webhook BCM:", e)
            register_in_txt(f"Error de seguridad en webhook BCM: {e}", "logs_bcm.txt")
            enviar_alerta(f"❌ Error de seguridad en webhook BCM: {e}")
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        
        if hasattr(g, "bcm_raw_body") and g.bcm_raw_body:
            try:
                payload = json.loads(g.bcm_raw_body.decode("utf-8"))
            except Exception:
                payload = request.get_json(silent=True) or {}
        else:
            payload = request.get_json(silent=True) or {}


        # operation_id       = payload.get("operation_id")
        transaction_id     = payload.get("transaction_id")   # puede venir null
        cod_cliente        = payload.get("cod_cliente")      # p.ej. juicio_n
        estado_transaccion = (payload.get("estado_transaccion") or "").lower()
        ts                 = payload.get("timestamp")
        notif_type         = payload.get("notification_type")

    
        # 1) si operation_id es nuestro uuid, lo usamos directo
        df = None

        if not cod_cliente:
            print("❌ cod_cliente ausente en webhook BCM" , cod_cliente)
            return jsonify({"ok": False, "error": "cod_cliente ausente"}), 400

        # df = DerechoFijoModel.query.filter_by(pay=cod_cliente).first()
        
        
            # buscamos el último recibo de ese DF
        receipt = (
        ReceiptModel.query
        .filter_by(payment_id=cod_cliente)
        .order_by(desc(ReceiptModel.fecha_pago))
        .first()
        )
        if receipt:
        # si la Bolsa dice pagado, marcamos Pagado
            if estado_transaccion in ("pagado", "aprobado", "approved", "aprobada"):
                if (receipt.status or "").lower() != "pagado":
                    receipt.status = "Pagado"
                    receipt.fecha_pago = datetime.utcnow()
                    db.session.add(receipt)
                    db.session.commit()
                    print(f"✅ Recibo {cod_cliente} marcado como Pagado por BCM.")

                    ## Envio de mails
                    enviar_comprobante_pago_por_mail(receipt.uuid_derecho_fijo, receipt.payment_method, cod_cliente)

                    return jsonify({"ok": True}), 200


                # si ya estaba Pagado, no se actualiza

                print(f"ℹ️ Recibo {cod_cliente} ya estaba Pagado, no se actualiza.")
                enviar_comprobante_pago_por_mail(receipt.uuid_derecho_fijo, receipt.payment_method, cod_cliente)
                return jsonify({"ok": True}), 200

            else:
                print(f"ℹ️ Recibo {cod_cliente} no actualizado, estado BCM: {estado_transaccion}")
                return jsonify({"ok": False, "error": "El recibo no se pudo actualizar. El status enviado no coincide con los siguientes (pagado, aprobado, approved)"}), 409
        else:
            print(f"❌ No se encontró recibo para payment_id {9321747794} (juicio_n={df.juicio_n})")
            return jsonify({"ok": False, "error": "No se encontró recibo para el DerechoFijo asociado."}), 404

                # si vino “fallido”, podrías guardar “Rechazado”/“Fallido” (opcional)



    except Exception as e:
        print("❌ Error en bcm_webhook_oficial:", e)
        traceback.print_exc()
        register_in_txt(f"Error en bcm_webhook_oficial: {e}", "logs_bcm.txt")
        enviar_alerta(f"❌ Error en bcm_webhook_oficial: {e}")
        return jsonify({"ok": "False",
                        "error": "InternalError"}), 500






def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except Exception:
        return False


@forms_bp.route('/forms/download_receipt', methods=['GET'])
def download_receipt():
    try:
        uuid_recibo = request.args.get("receipt_uuid")
        uuid_formulario = request.args.get("derecho_fijo_uuid")

        receipt = None
        derecho_fijo = None

        # Opción 1: buscar por recibo
        if uuid_recibo:
            receipt = ReceiptModel.query.filter_by(uuid=uuid_recibo).first()
            if not receipt:
                return jsonify({"error": "Recibo no encontrado"}), 404
            
            derecho_fijo = DerechoFijoModel.query.filter_by(uuid=receipt.uuid_derecho_fijo).first()
            if not derecho_fijo:
                return jsonify({"error": "Formulario vinculado no encontrado"}), 404

        # Opción 2: buscar por formulario
        elif uuid_formulario:
            derecho_fijo = DerechoFijoModel.query.get(uuid_formulario)
            if not derecho_fijo:
                return jsonify({"error": "Formulario no encontrado"}), 404

            receipt = ReceiptModel.query.filter_by(uuid_derecho_fijo=uuid_formulario).first()

        else:
            return jsonify({"error": "Debes enviar receipt_uuid o derecho_fijo_uuid como parámetro"}), 400

        # Datos de pago
        payment_data = {
            "id": receipt.payment_id if receipt else "N/A",
            "status": receipt.status if receipt else "N/A"
        }

        # Generar el PDF
        pdf_buffer = generate_receipt_pdf(payment_data, derecho_fijo)

        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"recibo_{receipt.receipt_number if receipt else uuid_formulario}.pdf"
        )

    except Exception as e:
        print("❌ Error confirmando recibo de forma remota:", e)
        enviar_alerta(f"❌ Error confirmando recibo de forma remota: {uuid_recibo}\n> uuid_formulario: {uuid_formulario}")
        register_in_txt(f"Error confirmando recibo de forma remota:\n> uuid_recibo: {uuid_recibo}\n> uuid_formulario: {uuid_formulario}", "logs_bcm.txt")
        return jsonify({"error": str(e)}), 500


from reportlab.graphics.barcode import code128
from reportlab.graphics.shapes import Drawing

###====== Deprecado, se deja en caso de haber mal funcionamiento con la original =======##

def generar_boleta_pdf_con_codigo(derecho_fijo, codigo_barra):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Encabezado
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "Boleta de Pago Presencial")
    c.setFont("Helvetica", 12)
    c.drawString(100, 730, f"Expediente: {derecho_fijo.juicio_n}")
    c.drawString(100, 710, f"Carátula: {derecho_fijo.caratula}")
    c.drawString(100, 690, f"Importe a pagar: ${derecho_fijo.total_depositado}")

    # Código de barras
    barcode = code128.Code128(codigo_barra, barHeight=40)
    barcode.drawOn(c, 100, 600)

    # Pie de página
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(100, 570, "Presente esta boleta en la Bolsa de Comercio para realizar el pago.")

    c.save()
    buffer.seek(0)
    return buffer

##=====================================================================================##

from io import BytesIO
def _make_qr_png_bytes(qr_payload, box_size=8, border=2, err=qrcode.constants.ERROR_CORRECT_M):
    qr = qrcode.QRCode(version=None, error_correction=err, box_size=box_size, border=border)
    qr.add_data(qr_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def generar_boleta_pdf_con_estilo(derecho_fijo, codigo_barra: str, qr_payload: str = None):  # <<<
    """
    Genera un PDF de boleta con:
      - Encabezado con logo y título
      - Bloques de Datos del expediente y Datos de pago
      - Monto destacado
      - Código de barras centrado + legible
      - Instrucciones
      - Línea de corte y Talón para caja (con mini código de barras)
      - (Opcional) QR grande y mini‑QR en talón si se envía `qr_payload`  # <<<
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- Config ---
    MARGIN = 15 * mm
    BOX_RADIUS = 6
    LIGHT_BORDER = colors.HexColor("#E5E7EB")
    PRIMARY = colors.HexColor("#06092E")
    ACCENT = colors.HexColor("#4F46E5")
    TEXT = colors.HexColor("#111827")

    c.setTitle("Boleta de Pago - Bolsa de Comercio")

    # --- Logos ---
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_left = os.path.join(base_dir, "utils", "assets", "logo-violeta.png")

    def try_draw_image(path, x, y, w, h):
        if os.path.exists(path):
            try:
                c.drawImage(path, x, y, width=w, height=h, preserveAspectRatio=True, mask='auto')
            except:
                pass

    # --- Encabezado ---
    header_h = 32 * mm
    c.setFillColor(colors.white)
    c.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
    c.setStrokeColor(LIGHT_BORDER)
    c.setLineWidth(1)
    c.line(MARGIN, height - header_h, width - MARGIN, height - header_h)
    try_draw_image(logo_left, MARGIN, height - 26*mm, 24*mm, 24*mm)

    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(MARGIN + 30*mm, height - 14*mm, "COLEGIO PÚBLICO DE ABOGADOS Y PROCURADORES")
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(ACCENT)
    c.drawString(MARGIN + 30*mm, height - 20*mm, "Segunda Circunscripción Judicial - Mendoza")
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(MARGIN, height - header_h - 8*mm, "Boleta de Pago Presencial – Bolsa de Comercio")

    def rounded_box(x, y, w, h, stroke=LIGHT_BORDER, fill=None):
        c.setStrokeColor(stroke)
        c.setFillColor(fill if fill else colors.white)
        c.setLineWidth(1)
        c.roundRect(x, y, w, h, BOX_RADIUS, stroke=1, fill=1)

    def label_value(x, y, label, value, lw=110):
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawString(x, y, label)
        c.setFont("Helvetica", 10)
        c.setFillColor(TEXT)
        c.drawString(x + lw, y, value if value is not None else "-")

    # --- Bloque Datos del expediente ---
    top = height - header_h - 14*mm
    box1_h = 48*mm
    rounded_box(MARGIN, top - box1_h, width - 2*MARGIN, box1_h)
    c.setFont("Helvetica-Bold", 11); c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6*mm, top - 7*mm, "Datos del expediente")
    c.setFillColor(TEXT)

    y = top - 15*mm
    left_x = MARGIN + 8*mm
    col2_x = width/2 + 2*mm
    label_value(left_x, y, "N° de Expediente:", getattr(derecho_fijo, "juicio_n", ""))
    label_value(col2_x, y, "Juzgado:", getattr(derecho_fijo, "juzgado", ""))

    y -= 7*mm
    label_value(left_x, y, "Carátula:", getattr(derecho_fijo, "caratula", ""))
    label_value(col2_x, y, "Parte:", getattr(derecho_fijo, "parte", ""))

    y -= 7*mm
    fi = getattr(derecho_fijo, "fecha_inicio", None)
    fv = getattr(derecho_fijo, "fecha", None)
    fi_str = fi.strftime("%d/%m/%Y") if fi else "-"
    fv_str = fv.strftime("%d/%m/%Y") if fv else "-"
    label_value(left_x, y, "Fecha Inicio:", fi_str)
    label_value(col2_x, y, "Fecha Vencimiento:", fv_str)

    y -= 7*mm
    label_value(left_x, y, "Lugar:", getattr(derecho_fijo, "lugar", ""))

    # --- Bloque Datos de pago + Monto ---
    box2_h = 34*mm
    top2 = top - box1_h - 6*mm
    rounded_box(MARGIN, top2 - box2_h, width - 2*MARGIN, box2_h)
    c.setFont("Helvetica-Bold", 11); c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6*mm, top2 - 7*mm, "Datos de pago")
    c.setFillColor(TEXT)

    y2 = top2 - 15*mm
    label_value(MARGIN + 8*mm, y2, "Tasa de justicia:", f"$ {getattr(derecho_fijo, 'tasa_justicia', '0')}")
    label_value(width/2 - 9*mm, y2, "Derecho fijo 5%:", f"$ {getattr(derecho_fijo, 'derecho_fijo_5pc', '0')}")

    amount_box_w = 70*mm
    amount_box_h = 18*mm
    amount_box_x = width - MARGIN - amount_box_w - 4
    amount_box_y = top2 - amount_box_h - 10*mm
    rounded_box(amount_box_x, amount_box_y, amount_box_w, amount_box_h, stroke=ACCENT)
    c.setFillColor(ACCENT); c.setFont("Helvetica-Bold", 10)
    c.drawString(amount_box_x + 6, amount_box_y + amount_box_h - 6*mm, "Importe a pagar")
    c.setFillColor(TEXT); c.setFont("Helvetica-Bold", 14)
    c.drawRightString(amount_box_x + amount_box_w - 6, amount_box_y + 6, f"$ {getattr(derecho_fijo, 'total_depositado', '0')}")

    # --- Código de barras (principal) ---
    top3 = top2 - box2_h - 8*mm
    barcode = code128.Code128(codigo_barra, barHeight=18*mm, barWidth=0.5)
    bw = barcode.width
    bx = (width - bw) / 7
    by = top3 - 17*mm
    barcode.drawOn(c, bx, by)
    c.setFont("Helvetica", 9); c.setFillColor(colors.HexColor("#4B5563"))
    c.drawCentredString(width/3.5, by - 4*mm, codigo_barra)

    # --- QR grande (opcional) ---  # <<<
    if qr_payload:
        try:
            qr_buf = _make_qr_png_bytes(qr_payload, box_size=8, border=2)
            qr_img = ImageReader(qr_buf)
            qr_size = 25 * mm                     # recomendado ≥ 30–35 mm
            qr_x = width - 30*mm - qr_size        # margen derecho
            qr_y = by + (mm - 10)                     # sobre el barcode
            c.drawImage(qr_img, qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True, mask='auto')
            c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#6B7280"))
            c.drawCentredString(qr_x + qr_size/2, qr_y - 10, "Escanear en caja")
        except Exception as e:
            print("⚠️ Error dibujando QR:", e)

    # --- Instrucciones ---
    instr_top = by - 14*mm
    rounded_box(MARGIN, instr_top - 22*mm, width - 2*MARGIN, 28*mm)
    c.setFont("Helvetica-Bold", 10); c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6*mm, instr_top - 1*mm, "Instrucciones")
    c.setFillColor(TEXT); c.setFont("Helvetica", 9)
    lines = [
        "• Presentar esta boleta en la Bolsa de Comercio para efectuar el pago.",
        "• La boleta es válida hasta la fecha de vencimiento indicada.",
        "• Conserve el talón inferior sellado como comprobante de pago.",
    ]
    yy = instr_top - 6*mm
    for line in lines:
        c.drawString(MARGIN + 8*mm, yy, line)
        yy -= 5*mm

    # --- Línea de corte ---
    cut_y = instr_top - 26*mm
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setDash(2, 2); c.line(MARGIN, cut_y, width - MARGIN, cut_y); c.setDash()
    c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#6B7280"))
    c.drawCentredString(width/2, cut_y - 4*mm, "— — — — — — — — — — — —  Corte aquí  — — — — — — — — — — — —")

    # --- Talón para caja ---
    slip_h = 40*mm
    slip_y = cut_y - slip_h - 6*mm
    rounded_box(MARGIN, slip_y, width - 2*MARGIN, slip_h)

    c.setFillColor(PRIMARY); c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 6*mm, slip_y + slip_h - 7*mm, "Talón para caja – Bolsa de Comercio")
    c.setFillColor(TEXT); c.setFont("Helvetica", 9)

    ty = slip_y + slip_h - 14*mm
    label_value(MARGIN + 8*mm, ty, "Expediente:", getattr(derecho_fijo, "juicio_n", ""))
    ty -= 6*mm
    label_value(MARGIN + 8*mm, ty, "Carátula:", (getattr(derecho_fijo, "caratula", "") or "")[:45])
    ty -= 6*mm
    label_value(MARGIN + 8*mm, ty, "Importe:", f"$ {getattr(derecho_fijo, 'total_depositado', '0')}")

    # mini código de barras
    mini = code128.Code128(codigo_barra, barHeight=12*mm, barWidth=0.45)
    mini_x = width - MARGIN - mini.width - 10
    mini_y = slip_y + 8*mm
    mini.drawOn(c, mini_x, mini_y)
    c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#4B5563"))
    c.drawRightString(mini_x + mini.width - 15, mini_y - 10, codigo_barra)

    # # mini‑QR en talón (opcional)  # <<<
    # if qr_payload:
    #     try:
    #         mini_qr_buf = _make_qr_png_bytes(qr_payload, box_size=5, border=2)
    #         mini_qr_img = ImageReader(mini_qr_buf)
    #         mini_qr_size = 26 * mm
    #         mini_qr_x = mini_x - 6 - mini_qr_size    # a la izquierda del mini-barcode
    #         mini_qr_y = slip_y + 7*mm
    #         c.drawImage(mini_qr_img, mini_qr_x, mini_qr_y, width=mini_qr_size, height=mini_qr_size, preserveAspectRatio=True, mask='auto')
    #     except Exception as e:
    #         print("⚠️ Error dibujando mini‑QR:", e)

    # Footer
    c.setFillColor(colors.HexColor("#9CA3AF")); c.setFont("Helvetica", 8)
    c.drawCentredString(width/2, 10*mm, "Colegio Público de Abogados y Procuradores – 2° Circ. Judicial (Mendoza)")

    c.showPage(); c.save(); buffer.seek(0)
    return buffer


def generate_receipt_pdf( payment_data, derecho_fijo):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    print(derecho_fijo, f"este e")
    # Obtener la ruta del logo
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Sube un nivel desde 'routes/'
    logo_path = os.path.join(base_dir, "utils", "assets", "logo-violeta.png")


    # Cargar el logo si existe
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 40, 750, width=120, height=120, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Error al cargar el logo: {e}")
    else:
        print(f"⚠️ No se encontró el logo en: {logo_path}")

        # Obtener la ruta de la segunda imagen (lado derecho)
    otro_logo_path = os.path.join(base_dir, "utils", "assets", "pagado.jpg")  # Ajusta el nombre del archivo

    # Cargar el segundo logo si existe
    if os.path.exists(otro_logo_path):
        try:
            c.drawImage(otro_logo_path, 450, 750, width=120, height=120, preserveAspectRatio=True, mask='auto')
        except Exception as e:
            print(f"Error al cargar el segundo logo: {e}")
    else:
        print(f"⚠️ No se encontró el segundo logo en: {otro_logo_path}")

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, 750, "COLEGIO PÚBLICO DE ABOGADOS Y")
    c.drawString(100, 730, "PROCURADORES")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(450, 750, "DERECHO FIJO")

    c.setFont("Helvetica", 12)
    c.drawString(100, 700, "Segunda Circunscripción Judicial - Mendoza")

    # Main content
    y = 650
    c.setFont("Helvetica-Bold", 10)

    # Verificar que las fechas no sean None
    fecha_inicio = getattr(derecho_fijo, 'fecha_inicio', None)
    fecha = getattr(derecho_fijo, 'fecha', None)

    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d") if fecha_inicio else "No disponible"
    fecha_str = fecha.strftime("%Y-%m-%d") if fecha else "No disponible"
    

    fields = [
        ("Fecha Inicio:", fecha_inicio_str),
        ("Fecha Vencimiento:", fecha_str),
        ("Caratula:", getattr(derecho_fijo, 'caratula', 'No disponible')),
        ("TOTAL DEPOSITADO:", f"$ {getattr(derecho_fijo, 'total_depositado', '0')}"),
        ("Juzgado:", getattr(derecho_fijo, 'juzgado', 'No disponible')),
        ("¿Paga tasa de justicia?", "Sí"),
        ("Monto:", getattr(derecho_fijo, 'tasa_justicia', '0')),
        ("N° de Expediente", getattr(derecho_fijo, 'juicio_n', 'No disponible')),
        ("ID de Pago:", payment_data.get('id', 'No disponible')),
        ("Fecha de Pago:", (derecho_fijo.created_at - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M") if derecho_fijo.created_at else "No disponible")

    ]

    for label, value in fields:
        c.drawString(100, y, label)
        c.setFont("Helvetica", 10)
        c.drawString(250, y, str(value))
        c.setFont("Helvetica-Bold", 10)
        y -= 20

    c.save()
    buffer.seek(0)
    return buffer

def get_relevant_rates(start_date: datetime, end_date: datetime, rate_type: RateType) -> List[RateModel]:
    """Get all relevant rates for the given period and rate type"""
    return RateModel.query.filter(
        and_(
            RateModel.rate_type == rate_type,
            RateModel.deleted_at.is_(None),
            RateModel.start_date <= end_date,
            or_(
                RateModel.end_date.is_(None),
                RateModel.end_date >= start_date
            )
        )
    ).order_by(RateModel.start_date.asc()).all()

def calculate_period_rate(rate: float, start_date: datetime, end_date: datetime) -> float:
    """Calculate the rate for a specific period: (yearly_rate/365) * days"""
    days = (end_date - start_date).days
    return (rate / 365) * days

def period_to_string(start_date: datetime, end_date: datetime, rate: float) -> str:
    """Format period details as string"""
    days = (end_date - start_date).days
    period_rate = calculate_period_rate(rate, start_date, end_date)
    return f"{start_date.strftime('%d/%m/%Y')} .. {end_date.strftime('%d/%m/%Y')}: ({rate}% / 365) x {days} días = {period_rate:.4f}%"


@forms_bp.route('/forms/confirm_receipt', methods=['POST'])
def confirm_receipt():
    uuid = None
    payment_id = None
    try:
        data = request.json
        uuid = data.get("uuid")
        payment_id = data.get("payment_id")

        if not uuid or not payment_id:
            return jsonify({"error": "Faltan datos"}), 400

        derecho_fijo = DerechoFijoModel.query.get(uuid)
        if not derecho_fijo:
            return jsonify({"error": "Derecho Fijo no encontrado"}), 404

        print("Confirmando recibo para derecho fijo:", derecho_fijo.uuid)
        print("derecho_fijo:", derecho_fijo,
              "uuid_derecho_fijo:", uuid,
              "payment_id:", payment_id,
              "status:", "Pagado")

        save_receipt_to_db(
            db_session=db.session,
            derecho_fijo=derecho_fijo,
            payment_id=payment_id,
            status="Pagado"
        )

        return jsonify({"message": "Recibo guardado exitosamente"}), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error al confirmar recibo:", e)
        enviar_alerta(f"❌ Error al confirmar recibo:\n> uuid:{uuid}\npayment_id:{payment_id}\n> error:{e}")
        register_in_txt(f"Error al confirmar recibo:\n> uuid:{uuid}\npayment_id:{payment_id}\n> error:{e}", "logs_bcm.txt")
        return jsonify({"error": str(e)}), 500

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.units import inch
from io import BytesIO
from PIL import Image as PILImage
import os
import uuid

def build_bolsa_payload_local(derecho_fijo, convenio="CBAMZA", version="1"):
    """
    Arma un payload QR/Barcode en texto siguiendo especificación de la Bolsa.
    👇 Reemplazar campos cuando te pasen el formato final.
    """
    monto = str(getattr(derecho_fijo, "total_depositado", "0"))
    venc  = getattr(derecho_fijo, "fecha", None)
    venc_yyyymmdd = venc.strftime("%Y%m%d") if venc else datetime.utcnow().strftime("%Y%m%d")
    # Ejemplo: TLV-like simple | prefijo|uuid|monto|venc|ver
    barcode_string = f"{convenio}|{derecho_fijo.uuid[:12]}|{monto}|{venc_yyyymmdd}|{version}"
    qr_payload     = barcode_string  # muchas Bolsas usan el mismo dato para QR y barras
    return barcode_string, qr_payload





def save_receipt_to_db(db_session, derecho_fijo, payment_id, status="Pendiente", payment_method="Mercado Pago(QR)"):
    from models import ReceiptModel
    from datetime import datetime

    receipt_id = None

    try:
        # 🚨 Validar si ya existe un recibo asociado a este derecho_fijo
        existing_by_form = ReceiptModel.query.filter_by(uuid_derecho_fijo=derecho_fijo.uuid).first()
        if existing_by_form:
            print(f"⚠️ Ya existe un recibo para el uuid {derecho_fijo.uuid}. Ignorando nuevo pago.")
            return  # Salida temprana

        # Validar si el payment ya se procesó por si llega duplicado
        existing_receipt = ReceiptModel.query.filter_by(payment_id=payment_id).first()
        if existing_receipt:
            if existing_receipt.status != status:
                print("ℹ️ Recibo existente con estado diferente. Actualizando...")
                existing_receipt.status = status
                existing_receipt.fecha_pago = datetime.now()
                db_session.commit()
                print(f"🔁 Recibo actualizado: {existing_receipt.receipt_number} → status: {status}")
            else:
                print("ℹ️ Recibo ya existente con mismo estado. No se modifica.")
            return

        receipt_id = str(uuid.uuid4())
        new_receipt = ReceiptModel(
            receipt_number=f"REC-{receipt_id[:8]}",
            uuid_derecho_fijo=derecho_fijo.uuid,
            fecha_inicio=derecho_fijo.fecha_inicio,
            fecha_vencimiento=derecho_fijo.fecha,
            caratula=derecho_fijo.caratula,
            total_depositado=derecho_fijo.total_depositado,
            tasa_justicia=derecho_fijo.tasa_justicia,
            juicio_n=derecho_fijo.juicio_n,
            payment_id=payment_id,
            fecha_pago=datetime.now(),
            status=status,
            payment_method=payment_method
        )

        db_session.add(new_receipt)
        db_session.commit()
        print(f"✅ Recibo guardado con status: {status}")

    except Exception as e:
        print("❌ Error guardando recibo:", e)
        enviar_alerta(f"❌ Error guardando recibo:\n> Recibo:{receipt_id or 'No generado'}\n> Error: {e}")
        register_in_txt(f"Error guardando recibo:\n> Recibo:{receipt_id or 'No generado'}\n> Error: {e}", "logs_bcm.txt")
        db_session.rollback()

# FUNCION Q GENERA EL PDF DE LIQ
def generate_liquidacion_pdf( capital: float, fecha_origen: datetime, fecha_liquidacion: datetime, 
                          detalles: list, tasa_total: float, monto_final: float) -> BytesIO:
   # Create a buffer to receive PDF data
   buffer = BytesIO()
   
   # Create the PDF object
   doc = SimpleDocTemplate(
       buffer,
       pagesize=letter,
       rightMargin=72,
       leftMargin=72,
       topMargin=72,
       bottomMargin=72
   )
   
   # Container for the 'Flowable' objects
   elements = []
   
   # Define styles
   styles = getSampleStyleSheet()
   title_style = ParagraphStyle(
       'CustomTitle',
       parent=styles['Heading1'],
       fontSize=14,
       spaceAfter=30
   )
   normal_style = ParagraphStyle(
       'CustomNormal',
       parent=styles['Normal'],
       fontSize=12,
       spaceAfter=12
   )
   
   # Process and add logo
   utils_dir = os.path.dirname(os.path.abspath(__file__))
   logo_path = os.path.join(utils_dir, 'assets', 'logo-grande.png')
   
   if os.path.exists(logo_path):
       # Open and convert image to black
       with PILImage.open(logo_path) as img:
           # Convert to grayscale then to black
           img = img.convert('L')  # Convert to grayscale
           # Convert to black (threshold at 128)
           img = img.point(lambda x: 0 if x > 128 else 255, '1')
           
           # Save to temporary buffer
           temp_buffer = BytesIO()
           img.save(temp_buffer, format='PNG')
           temp_buffer.seek(0)
           
           # Create reportlab image
           logo = Image(temp_buffer)
           # Set dimensions (adjust as needed)
           logo.drawHeight = 1*inch
           logo.drawWidth = 1.5*inch
           elements.append(logo)
           elements.append(Spacer(1, 20))
   
   # Add title
   elements.append(Paragraph("Colegio de Abogados de Mendoza - Formularios", title_style))
   elements.append(Spacer(1, 12))
   
   # Add calculation title
   elements.append(Paragraph("Cálculo de liquidación", title_style))
   elements.append(Spacer(1, 12))
   
   # Add basic information
   elements.append(Paragraph(f"Capital (pesos) {capital}$", normal_style))
   elements.append(Paragraph("Tasa utilizada: Tasa Banco Nación Activa", normal_style))
   elements.append(Paragraph(f"Fecha de origen: {fecha_origen.strftime('%d/%m/%Y')}", normal_style))
   elements.append(Paragraph(f"Fecha de liquidación: {fecha_liquidacion.strftime('%d/%m/%Y')}", normal_style))
   elements.append(Spacer(1, 12))
   
   # Add rate details
   for detalle in detalles:
       elements.append(Paragraph(detalle, normal_style))
   
   # Add total rate
   elements.append(Spacer(1, 12))
   tasa_efectiva = (tasa_total / capital) * 100
   elements.append(Paragraph(f"Tasa de interés: {tasa_efectiva:.2f}%", normal_style))
   elements.append(Spacer(1, 12))
   
   # Add final amount
   elements.append(Paragraph(f"Interés: {int(monto_final - capital)}$", normal_style))
   elements.append(Paragraph("=========", normal_style))
   elements.append(Paragraph(f"Monto Final: {int(monto_final)}$", normal_style))
   
   # Add footer
   elements.append(Spacer(1, 30))
   elements.append(Spacer(1, 12))
   footer_style = ParagraphStyle(
       'Footer',
       parent=styles['Normal'],
       fontSize=10,
       alignment=1  # Center alignment
   )
   elements.append(Paragraph("Segunda Circunscripción Judicial de Mendoza", footer_style))
   elements.append(Paragraph("(San Rafael - Gral. Alvear - Malargüe)", footer_style))
   
   # Build PDF
   doc.build(elements)
   buffer.seek(0)
  

   return buffer

def calculate_bank_rate(capital_inicial: float, fecha_origen: datetime, fecha_liquidacion: datetime, frecuencia_aplicacion: float = 1):
    """Handle 'tasa_bancaria' calculation type"""
    # Get rates from database
    rates = get_relevant_rates(fecha_origen, fecha_liquidacion, RateType.ACTIVABNA)
    if not rates:
        raise ValueError("No se encontraron tasas para el período especificado")

    # Calculate periods and rates
    total_rate = 0
    detalles = []
    current_date = fecha_origen

    for i, rate in enumerate(rates):
        rate_start = max(rate.start_date, current_date)
        
        if i < len(rates) - 1:
            period_end = min(rates[i + 1].start_date, fecha_liquidacion)
        else:
            period_end = fecha_liquidacion

        if rate_start < period_end:
            period_rate = calculate_period_rate(float(rate.rate), rate_start, period_end)
            total_rate += period_rate
            detalles.append(period_to_string(rate_start, period_end, float(rate.rate)))

        current_date = period_end
        if current_date >= fecha_liquidacion:
            break

    # Apply frecuencia_aplicacion to total_rate
    total_rate = total_rate * frecuencia_aplicacion
    
    # Calculate final amount
    monto_final = capital_inicial * (1 + total_rate / 100)
    
    return total_rate, detalles, monto_final

def calculate_yearly_rate(capital_inicial: float, fecha_origen: datetime, fecha_liquidacion: datetime, interes_anual: float):
    """Handle 'interes_anual' calculation type"""
    # Calculate days between dates
    days = (fecha_liquidacion - fecha_origen).days
    
    # Calculate rate for the period
    total_rate = (interes_anual / 365) * days
    
    # Create detail string
    detalle = f"{fecha_origen.strftime('%d/%m/%Y')} .. {fecha_liquidacion.strftime('%d/%m/%Y')}: ({interes_anual}% / 365) x {days} días = {total_rate:.4f}%"
    
    # Calculate final amount
    monto_final = capital_inicial * (1 + total_rate / 100)
    
    return total_rate, [detalle], monto_final

@forms_bp.route('/forms/liquidaciones', methods=['POST'])
def generar_liquidaciones():
    try:
        data = request.json
        capital_inicial = float(data.get('importe_inicial'))
        fecha_origen = datetime.strptime(data.get('fecha_inicio'), '%d/%m/%Y')
        fecha_liquidacion = datetime.strptime(data.get('fecha_final'), '%d/%m/%Y')
        tipo_calculo = data.get('tipo_calculo')
        
        if not all([capital_inicial, fecha_origen, fecha_liquidacion, tipo_calculo]):
            return jsonify({
                "error": "Faltan parámetros requeridos"
            }), 400

        # Calculate based on type
        if tipo_calculo == "tasa_bancaria":
            frecuencia_aplicacion = float(data.get('frecuencia_aplicacion', 1))
            total_rate, detalles, monto_final = calculate_bank_rate(
                capital_inicial, 
                fecha_origen, 
                fecha_liquidacion, 
                frecuencia_aplicacion
            )
        elif tipo_calculo == "interes_anual":
            interes_anual = float(data.get('interes_anual'))
            if not interes_anual:
                return jsonify({"error": "Interés anual es requerido"}), 400
            total_rate, detalles, monto_final = calculate_yearly_rate(
                capital_inicial,
                fecha_origen,
                fecha_liquidacion,
                interes_anual
            )
        else:
            return jsonify({"error": "Tipo de cálculo no válido"}), 400

        # Generate PDF
        pdf_buffer = generate_liquidacion_pdf(
            capital=capital_inicial,
            fecha_origen=fecha_origen,
            fecha_liquidacion=fecha_liquidacion,
            detalles=detalles,
            tasa_total=total_rate,
            monto_final=monto_final
        )
        
        filename = f"Liquidacion-{fecha_origen.strftime('%d-%m-%Y')}-{fecha_liquidacion.strftime('%d-%m-%Y')}.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except ValueError as e:
        print("Error de validación:", e)
        enviar_alerta(f"Error de validación (/forms/liquidaciones):{e}")
        register_in_txt("Error de validación (/forms/liquidaciones):" + str(e), "logs_bcm.txt")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print("Error en el cálculo de liquidación:", e)
        enviar_alerta(f"Error en el calculo de la liquidacion: {e}")
        register_in_txt("Error en el cálculo de liquidación: " + str(e), "logs_bcm.txt")
        return jsonify({"error": str(e)}), 500
    

from flask import Blueprint, request, jsonify
import logging
import random
import time
import traceback
from playwright.sync_api import sync_playwright
import re


# FUNC Q PARSEA EL RESULTADO DEL SCRAPP DE LIQ A UN JSON MAS LIMPIO
def parse_resultado_html(resultado_html):
    resultado = {
        "detalle": [],
        "calculo_intereses": [],
        "interes_total": None,
        "total_final": None
    }

    html = resultado_html.replace('\n', '').replace('\t', '').strip()

    # 1. Datos fijos (tipo descripcion + valor)
    matches_fijos = re.findall(r'<tr><td>([^<]+)</td><td[^>]*>([^<]*)</td></tr>', html)
    for desc, val in matches_fijos:
        texto = desc.strip().replace("&nbsp;", "")
        valor = val.strip().replace("&nbsp;", "")
        if "Tasa de interés" in texto:
            resultado["interes_total"] = int(valor)
        elif valor == "==========" or valor == "":
            continue
        elif texto == "":
            resultado["total_final"] = int(valor)
        else:
            fila = {"descripcion": texto}
            if valor:
                try:
                    fila["valor"] = int(valor)
                except:
                    fila["valor"] = valor
            resultado["detalle"].append(fila)

    # 2. Períodos con cálculo de interés
    matches_periodos = re.findall(
        r'<td[^>]*>(\d{2}/\d{2}/\d{4} .. \d{2}/\d{2}/\d{4}): \(([^)]+)\) x (\d+) días = ([\d.,]+%)</td>',
        html
    )

    for periodo, tasa, dias, resultado_porcentaje in matches_periodos:
        resultado["calculo_intereses"].append({
            "periodo": periodo,
            "tasa": tasa.strip(),
            "dias": int(dias),
            "resultado": resultado_porcentaje
        })

    return resultado

#Scraper de las liquidaciones a la otra web de colegio de abogados
# Funciones auxiliares
def human_delay(min_seconds=0.5, max_seconds=2.0):
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def move_mouse_randomly(page):
    page.mouse.move(
        random.randint(100, 500),
        random.randint(100, 500)
    )

def scroll_randomly(page):
    page.evaluate("window.scrollBy(0, {})".format(random.randint(100, 300)))
    human_delay(0.3, 1.0)

# Endpoint
@forms_bp.route('/forms/calcular_liquidacion', methods=['POST'])
def calcular_liquidacion():
    data = request.json
    logging.info(f"📨 Datos recibidos: {data}")
    concepto = data.get("concepto", "")
    tasa = data.get("tasa", "")
    capital = data.get("capital", 0)
    fecha_origen_str = data.get("fecha_origen", "")
    fecha_liquidacion_str = data.get("fecha_liquidacion", "")
    imprimir = data.get("imprimir", False)
    descargar_pdf = data.get("descargar_pdf", False)

    try:
        fecha_origen = datetime.strptime(fecha_origen_str, "%d/%m/%Y")
        fecha_liquidacion = datetime.strptime(fecha_liquidacion_str, "%d/%m/%Y")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                locale="es-AR",
                timezone_id="America/Argentina/Buenos_Aires"
            )
            context.set_extra_http_headers({
                "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"100\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\""
            })

            page = context.new_page()
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logging.info(f"🌐 Intento de navegación #{attempt+1}")
                    page.goto("https://tribunalesmza.com.ar/pdforms/calculo/form", timeout=60000)
                    if "Not Acceptable" in page.title():
                        logging.warning("⚠️ ModSecurity detectado, reintentando...")
                        human_delay(3, 5)
                        continue
                    break
                except Exception as e:
                    logging.error(f"🚧 Error al navegar: {str(e)}")
                    if attempt == max_retries - 1:
                        raise
                    human_delay(3, 5)

            page.screenshot(path="/tmp/initial_page.png")

            # Interacciones humanas simuladas
            human_delay()
            move_mouse_randomly(page)
            scroll_randomly(page)

            # Paso 1: click en primer botón
            page.wait_for_selector('a.btn-default', timeout=10000)
            page.hover('a.btn-default')
            human_delay()
            page.click('a.btn-default')
            logging.info("🖱 Click en botón inicial")

            human_delay(1, 3)
            move_mouse_randomly(page)

            # Paso 2: click en segundo botón
            page.wait_for_selector('a.btn-success', timeout=10000)
            page.hover('a.btn-success')
            human_delay()
            page.click('a.btn-success')
            logging.info("🖱 Click en botón 'Continuar'")

            human_delay(1, 2)
            logging.info("✏️ Rellenando formulario...")


            page.wait_for_selector('input[placeholder="Descripción del concepto a liquidar"]', timeout=10000)
            page.focus('input[placeholder="Descripción del concepto a liquidar"]')
            human_delay()
            page.fill('input[placeholder="Descripción del concepto a liquidar"]', concepto)

            human_delay()
            page.select_option('select', label=tasa)

            human_delay()
            page.focus('input[placeholder="Capital"]')
            page.fill('input[placeholder="Capital"]', str(capital))

            human_delay()
            page.focus('input[placeholder="Fecha de origen dd/mm/aaaa"]')
            page.fill('input[placeholder="Fecha de origen dd/mm/aaaa"]', fecha_origen_str)

            if imprimir:
                human_delay()
                page.check('input[type="checkbox"]')


            page.screenshot(path="/tmp/before_submit.png")


            # Submit
            human_delay(1, 2)
            page.hover('input#submit')
            human_delay()
            page.click('input#submit')
            logging.info("📤 Formulario enviado")

            human_delay(2, 4)

            with open("/tmp/page_after_submit.html", "w") as f:
                f.write(page.content())

            # Buscar tabla con resultados
            page.wait_for_selector('table', timeout=15000)
            tables = page.query_selector_all('table')
            logging.info(f"📊 Tablas encontradas: {len(tables)}")

            tabla_html = ""
            found_pesos_table = False
            for i, table in enumerate(tables):
                table_text = table.inner_text()
                if "pesos" in table_text.lower():
                    tabla_html = table.inner_html()
                    found_pesos_table = True
                    logging.info(f"✅ Tabla #{i} contiene 'pesos'")
                    break

            if not found_pesos_table:
                logging.warning("🚨 No se encontró tabla con 'pesos'. Reintentando con selector de texto...")
                try:
                    page.wait_for_selector('table:has-text("pesos")', timeout=20000)
                    tabla_html = page.inner_html('table:has-text("pesos")')
                except Exception as e:
                    page.screenshot(path="/tmp/no_table_found.png")
                    raise ValueError("No se encontró ninguna tabla válida con resultados.")

            browser.close()

        # Procesar HTML
        resultado = parse_resultado_html(tabla_html)

        if descargar_pdf:
            detalles = [f"{item['periodo']}: {item['resultado']}" for item in resultado.get("calculo_intereses", [])]
            tasa_total = resultado.get("interes_total", 0)
            monto_final = resultado.get("total_final", 0)

            pdf_buffer = generate_liquidacion_pdf(
                capital=float(capital),
                fecha_origen=fecha_origen,
                fecha_liquidacion=fecha_liquidacion,
                detalles=detalles,
                tasa_total=float(tasa_total),
                monto_final=float(monto_final)
            )

            pdf_size = pdf_buffer.getbuffer().nbytes
            if pdf_size < 1000:
                raise ValueError("PDF generado es sospechosamente pequeño.")

            return send_file(
                pdf_buffer,
                as_attachment=True,
                download_name="liquidacion.pdf",
                mimetype="application/pdf"
            )

        return jsonify({"ok": True, **resultado})

    except Exception as e:
        traceback.print_exc()
        logging.error(f"💥 Error completo: {str(e)}")
        enviar_alerta(f"💥 Error al calular liquidacion(/forms/calcular_liquidacion): {e}")
        register_in_txt(f"Error al calular liquidacion(/forms/calcular_liquidacion): {e}", "logs_bcm.txt")
        return jsonify({"ok": False, "error": str(e)})
    



@forms_bp.route('/forms/check_derecho_fijo', methods=['POST'])
def check_derecho_fijo():
    try:
        today = datetime.utcnow()
        primer_dia_mes = today.replace(day=10)
        max_dia_habil = primer_dia_mes + timedelta(days=5)
        print("Primer dia del mes: ", primer_dia_mes)

        # Validamos si estamos dentro de los primeros días del mes
        if today > max_dia_habil:
            return jsonify({"message": "No es necesario actualizar. Ya pasó el período inicial del mes."}), 200
        print(PriceDerechoFijo.fecha)
        # Revisamos si ya hay registro de este mes
        existe = PriceDerechoFijo.query.filter(
            db.extract('year', PriceDerechoFijo.fecha) == today.year,
            db.extract('month', PriceDerechoFijo.fecha) == today.month
        ).first()

        if existe:
            return jsonify({"message": "Ya existe valor cargado para este mes."}), 200

        # Buscamos el último valor anterior
        ultimo = PriceDerechoFijo.query \
            .filter(PriceDerechoFijo.fecha < primer_dia_mes) \
            .order_by(PriceDerechoFijo.fecha.desc()) \
            .first()

        if not ultimo:
            return jsonify({"error": "No hay valores anteriores para copiar."}), 400

        # Clonamos valor para el mes actual
        nuevo_valor = PriceDerechoFijo(
            fecha=primer_dia_mes,
            value=ultimo.value
        )
        db.session.add(nuevo_valor)
        db.session.commit()

        return jsonify({"message": "Valor copiado automáticamente", "nuevo": nuevo_valor.to_json()}), 201

    except Exception as e:
        db.session.rollback()
        print("❌ Error en check_derecho_fijo:", e)
        return jsonify({"error": str(e)}), 500
    


@forms_bp.route('/forms/update_derecho_fijo', methods=['POST'])
# @jwt_required()
# @token_required
# @access_required('')
def update_derecho_fijo():
    try:
        data = request.get_json()
        fecha_str = data.get("fecha")
        nuevo_valor = data.get("value")

        if not fecha_str or nuevo_valor is None:
            return jsonify({"error": "Faltan campos requeridos: 'fecha' y 'value'"}), 400

        # Parseamos fecha
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d")
        anio, mes = fecha.year, fecha.month

        # Buscamos si ya hay un valor para ese mes
        registro = PriceDerechoFijo.query.filter(
            db.extract('year', PriceDerechoFijo.fecha) == anio,
            db.extract('month', PriceDerechoFijo.fecha) == mes
        ).first()

        if registro:
            registro.value = nuevo_valor
            registro.fecha = fecha  # Por si quiere cambiar la fecha exacta
            message = "Valor actualizado exitosamente."
        else:
            registro = PriceDerechoFijo(fecha=fecha, value=nuevo_valor)
            db.session.add(registro)
            message = "Nuevo valor creado exitosamente."

        db.session.commit()
        return jsonify({"message": message, "data": registro.to_json()}), 200
    

    except Exception as e:
        db.session.rollback()
        print("❌ Error al actualizar derecho fijo:", e)
        return jsonify({"error": str(e)}), 500

@forms_bp.route("/forms/get_price_derecho_fijo", methods=['GET'])
def get_price_derecho_fijo():
    now = datetime.now()
    anio = now.year
    mes = now.month

    price = PriceDerechoFijo.query.filter(
        db.extract('year', PriceDerechoFijo.fecha) == anio,
        db.extract('month', PriceDerechoFijo.fecha) == mes
    ).all()

    if not price:
        return jsonify({"error": "La consulta a la base de datos vino vacía"}), 404

    data = [item.to_json() for item in price]

    return jsonify({"data": data}), 200

