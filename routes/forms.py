from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, send_file
from sqlalchemy import and_, or_
from config.config import db
from models import DerechoFijoModel, RateModel, ReceiptModel, PriceDerechoFijo
from utils.decorators import token_required, access_required
from flask_jwt_extended import jwt_required
from utils.errors import ValidationError
from config.config_mp import get_mp_sdk
import qrcode
import base64
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

forms_bp = Blueprint('forms_bp', __name__)


@forms_bp.route('/forms/derecho_fijo', methods=['POST'])
# @jwt_required()
# @token_required
# @access_required('')
def derecho_fijo():
    print("🔍 Headers:", request.headers)
    print("🔍 Raw body:", request.data)
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
                "email": data.get("email", "example@example.com")
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
        print("\n\nPreference creada:", preference_response, "\n\n")  # Debug log

        # Use init_point instead of point_of_interaction
        qr_code_url = preference_response["response"]["init_point"] # Cambiar para produccion
        # qr_code_url = preference_response["response"]["sandbox_init_point"]
    

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
        return jsonify({"Error:": str(e)}), 400
    except Exception as e:
        print("Error details:", e)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
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
                        save_receipt_to_db(db.session, derecho_fijo, payment_id)
                        print("✅ Recibo guardado correctamente.")
                    else:
                        print("❌ No se encontro el derecho fijo de uuid", external_reference)
            else:
                print("❌ Error al consultar el pago con Mercado Pago")

        return jsonify({"message": "Webhook processed"}), 200

    except Exception as e:
        print("Error manejando webhook:", e)
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
                    "status": payment['status']
                }), 200
        
        # If no payment found, return pending
        return jsonify({
            "status": "pending"
        }), 200
        
    except Exception as e:
        traceback.print_exc()  # Print the full traceback for debugging
        print("Error checking payment status:", str(e))
        return jsonify({"error": str(e)}), 500
    
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
        print("❌ Error generando recibo:", e)
        return jsonify({"error": str(e)}), 500


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
    try:
        data = request.json
        uuid = data.get("uuid")
        payment_id = data.get("payment_id")

        if not uuid or not payment_id:
            return jsonify({"error": "Faltan datos"}), 400

        derecho_fijo = DerechoFijoModel.query.get(uuid)
        if not derecho_fijo:
            return jsonify({"error": "Derecho Fijo no encontrado"}), 404

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
def save_receipt_to_db(db_session, derecho_fijo, payment_id, status="Pendiente"):
    from models import ReceiptModel
    from datetime import datetime
    
    try:
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
        status=status  # <- Este campo es el que da error si no lo incluís en la función
    )


        db_session.add(new_receipt)
        db_session.commit()
        print(f"✅ Recibo guardado con status: {status}")

    except Exception as e:
        print("❌ Error guardando recibo:", e)
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
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print("Error en el cálculo de liquidación:", e)
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

