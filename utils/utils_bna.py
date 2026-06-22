import os
import uuid
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.graphics.barcode import code128
from dotenv import load_dotenv

def generar_id_desde_uuid():
    # uuid.uuid4().int devuelve la versión numérica de 128 bits del UUID
    uuid_numerico = uuid.uuid4().int
    return str(uuid_numerico)[:10]

def generar_codigo_de_barras_bna(importe: str, id_transaction: str) -> str:
    """
    Esta funcion concatena id_operation, digito_control, cuenta_corriente, importe 
    e id_transaction con el fin de generar el codigo de barras que se imprimira 
    en la boleta fisica a pagar en Banco Nacion.
    
    Asegura que el codigo resultante sea puramente numerico y no exceda 
    el limite maximo de 29 caracteres, acortando id_transaction si es necesario.

    Parametros:
    -----------
    importe : str
        Importe de la transaccion que se esta generando
    id_transaction : str
        Identificador unico/UUID de la transaccion

    Returns
    -------
    str
        Codigo de barras numerico de maximo 29 caracteres
    """
    # Cargar variables de entorno (con fallbacks si no están definidas)
    id_operation = os.getenv("BNA_OPERATION_ID", "345")
    digito_control = os.getenv("BNA_DIGITO_CONTROL_INICIAL", "2")
    cuenta_corriente = os.getenv("CUENTA_CORRIENTE_COLEJUS", "35837320000973")

    id_op_clean = "".join(c for c in str(id_operation) if c.isdigit())
    dc_clean = "".join(c for c in str(digito_control) if c.isdigit())
    cc_clean = "".join(c for c in str(cuenta_corriente) if c.isdigit())
    
    imp_str = str(importe)
    if "." in imp_str or "," in imp_str:
        try:
            importe_centavos = int(float(imp_str.replace(",", ".")) * 100)
            imp_clean = str(importe_centavos)
        except ValueError:
            imp_clean = "".join(c for c in imp_str if c.isdigit())
    else:
        imp_clean = "".join(c for c in imp_str if c.isdigit())
        
    id_tx_clean = "".join(c for c in str(id_transaction) if c.isdigit())
    
    fixed_len = len(id_op_clean) + len(dc_clean) + len(cc_clean) + len(imp_clean)
    available_space = max(0, 29 - fixed_len)
    
    id_tx_shortened = id_tx_clean[:available_space]
    
    return f"{id_op_clean}{dc_clean}{cc_clean}{imp_clean}{id_tx_shortened}"


def formatear_moneda(valor) -> str:
    try:
        val_float = float(str(valor).replace(",", "."))
        formatted = f"{val_float:,.2f}"
        main_part, dec_part = formatted.rsplit(".", 1)
        main_part_swapped = main_part.replace(",", ".")
        return f"$ {main_part_swapped},{dec_part}"
    except (ValueError, TypeError):
        return f"$ {valor}"

def generar_boleta_pdf_bna(derecho_fijo, codigo_barra: str, qr_payload: str = None):
    """
    Genera el PDF de la boleta de pago presencial para el Banco de la Nacion Argentina.
    Cumple con todos los requisitos de identificacion institucional, datos de la
    cuenta recaudadora, datos de la transaccion, expediente y espacios de validacion.
    Carga todos los valores dinámicos y de configuración desde variables de entorno.
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

    # --- Configuración desde Variables de Entorno (con fallbacks) ---
    ins_name = os.getenv("INSTITUTION_NAME", "COLEGIO PÚBLICO DE ABOGADOS Y PROCURADORES")
    ins_sub = os.getenv("INSTITUTION_SUBTITLE", "2° Circunscripción Judicial - Mendoza")
    ins_slip_title = os.getenv("INSTITUTION_SLIP_TITLE", "Colegio Público de Abogados y Procuradores - 2° Circ. Judicial")
    
    bank_name = os.getenv("BNA_BANK_NAME", "Banco de la Nación Argentina (BNA)")
    bank_branch = os.getenv("BNA_BANK_BRANCH", "Tribunales San Rafael - Mendoza")
    account_type = os.getenv("BNA_ACCOUNT_TYPE", "Cuenta Corriente (Cta. Cte.)")
    account_short = os.getenv("BNA_ACCOUNT_SHORT_NAME", "Cuenta BNA")
    account_type_short = os.getenv("BNA_ACCOUNT_TYPE_SHORT", "Cta. Cte.")
    transaction_place = os.getenv("BNA_TRANSACTION_PLACE", "San Rafael")

    cc_env = os.getenv("CUENTA_CORRIENTE_COLEJUS", "35837320000973")
    cuenta_corriente_display = f"{cc_env[:4]}-{cc_env[4:]}" if (cc_env.isdigit() and len(cc_env) == 14) else cc_env

    c.setTitle(f"Boleta de Pago - {bank_name}")

    # --- Helpers de dibujo ---
    def try_draw_image(path, x, y, w, h):
        if os.path.exists(path):
            try:
                c.drawImage(path, x, y, width=w, height=h, preserveAspectRatio=True, mask='auto')
            except:
                pass

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

    def draw_label_value_wrapped(
        x, y, label, value, max_width,
        lw=80, font_name="Helvetica", font_size=10,
        leading=4 * mm, max_lines=4
    ):
        """
        Dibuja label + value en varias líneas (corta por caracteres).
        """
        value = (value or "").strip() or "-"
        # Label
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#6B7280"))
        c.drawString(x, y, label)

        # Valor envuelto
        c.setFont(font_name, font_size)
        c.setFillColor(TEXT)

        start_x = x + lw
        lines = []
        current = ""

        for ch in value:
            test = current + ch
            if c.stringWidth(test, font_name, font_size) <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = ch

        if current:
            lines.append(current)

        # Limitar cantidad de líneas
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            if not lines[-1].endswith("..."):
                lines[-1] = lines[-1] + " ..."

        for i, line in enumerate(lines):
            c.drawString(start_x, y - i * leading, line)

        return y - (len(lines) - 1) * leading

    # --- Logos ---
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_left = os.path.join(base_dir, "utils", "assets", "logo-violeta.png")

    # --- Encabezado ---
    header_h = 32 * mm
    c.setFillColor(colors.white)
    c.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
    c.setStrokeColor(LIGHT_BORDER)
    c.setLineWidth(1)
    c.line(MARGIN, height - header_h, width - MARGIN, height - header_h)

    # logo a la izquierda
    try_draw_image(logo_left, MARGIN + 10, height - 21 * mm, 22 * mm, 22 * mm)

    # textos centrados
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 21 * mm, ins_name)

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(ACCENT)
    c.drawCentredString(width / 2, height - 27 * mm, ins_sub)

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, height - header_h - 8 * mm,
                        f"Boleta de Pago Presencial – {bank_name}")

    # --- Bloque Datos del expediente y Transacción ---
    title_y = height - header_h - 8 * mm
    box1_top = title_y - 8 * mm
    box1_h = 48 * mm
    rounded_box(MARGIN, box1_top - box1_h, width - 2 * MARGIN, box1_h)

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6 * mm, box1_top - 7 * mm, "Datos del expediente y de la transacción")
    c.setFillColor(TEXT)

    y = box1_top - 14 * mm
    left_x = MARGIN + 8 * mm
    col2_x = width / 2 + 10 * mm

    fi_str = datetime.now().strftime("%d/%m/%Y") # Fecha de Emisión actual
    fv = getattr(derecho_fijo, "fecha", None)
    fv_str = fv.strftime("%d/%m/%Y") if fv else "-"

    label_value(left_x, y, "Juicio N° (Expediente):", getattr(derecho_fijo, "juicio_n", ""), lw=115)
    label_value(col2_x, y, "Fecha de Emisión:", fi_str, lw=110)

    # Carátula envuelta
    y -= 6 * mm
    caratula = getattr(derecho_fijo, "caratula", "")
    max_width_caratula = (width - 2 * MARGIN) - (left_x + 110)
    y = draw_label_value_wrapped(
        x=left_x,
        y=y,
        label="Carátula:",
        value=caratula,
        max_width=max_width_caratula,
        lw=110,
        font_size=10,
        leading=4 * mm,
        max_lines=3
    )

    # Juzgado envuelto
    y -= 5 * mm
    juzgado = getattr(derecho_fijo, "juzgado", "")
    y = draw_label_value_wrapped(
        x=left_x,
        y=y,
        label="Juzgado:",
        value=juzgado,
        max_width=max_width_caratula,
        lw=110,
        font_size=10,
        leading=4 * mm,
        max_lines=2
    )

    # Parte y Fecha de Vencimiento
    y -= 5 * mm
    label_value(left_x, y, "Parte:", getattr(derecho_fijo, "parte", ""), lw=110)
    label_value(col2_x, y, "Fecha de Vencimiento:", fv_str, lw=110)

    # Lugar
    y -= 6 * mm
    label_value(left_x, y, "Lugar:", transaction_place, lw=110)

    # --- Bloque Datos de la Cuenta Bancaria Recaudadora ---
    box2_top = box1_top - box1_h - 4 * mm
    box2_h = 26 * mm
    rounded_box(MARGIN, box2_top - box2_h, width - 2 * MARGIN, box2_h)

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6 * mm, box2_top - 6 * mm, "Datos de la cuenta bancaria recaudadora")
    c.setFillColor(TEXT)

    y2 = box2_top - 12 * mm
    label_value(left_x, y2, "Banco:", bank_name, lw=135)
    
    y2 -= 5 * mm
    label_value(left_x, y2, "Sucursal:", bank_branch, lw=135)
    
    y2 -= 5 * mm
    label_value(left_x, y2, "Tipo y Número de Cuenta:", f"{account_type} Nº {cuenta_corriente_display}", lw=135)

    # --- Bloque Datos de pago ---
    box3_top = box2_top - box2_h - 4 * mm
    box3_h = 26 * mm
    rounded_box(MARGIN, box3_top - box3_h, width - 2 * MARGIN, box3_h)

    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6 * mm, box3_top - 6 * mm, "Datos de pago")
    c.setFillColor(TEXT)

    y3 = box3_top - 13 * mm
    tasa_val = getattr(derecho_fijo, 'tasa_justicia', '0')
    derecho_fijo_val = float(getattr(derecho_fijo, 'total_depositado', '0')) * 0.05
    total_val = getattr(derecho_fijo, 'total_depositado', '0')

    label_value(left_x, y3, "Tasa de justicia:", formatear_moneda(tasa_val), lw=110)
    label_value(left_x, y3 - 5 * mm, "Derecho fijo 5%:", formatear_moneda(derecho_fijo_val), lw=110)

    amount_box_w = 70 * mm
    amount_box_h = 16 * mm
    amount_box_x = width - MARGIN - amount_box_w - 4 * mm
    amount_box_y = box3_top - amount_box_h - 6 * mm
    rounded_box(amount_box_x, amount_box_y, amount_box_w, amount_box_h, stroke=ACCENT)

    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(amount_box_x + 6, amount_box_y + amount_box_h - 5 * mm, "Importe a pagar")

    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(amount_box_x + amount_box_w - 6, amount_box_y + 4 * mm,
                      formatear_moneda(total_val))

    # --- Código de barras (principal) centrado ---
    barcode_top = box3_top - box3_h - 6 * mm
    barcode = code128.Code128(codigo_barra, barHeight=16 * mm, barWidth=0.5)
    bw = barcode.width
    bx = (width - bw) / 2
    by = barcode_top - 16 * mm
    barcode.drawOn(c, bx, by)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawCentredString(width / 2, by - 4 * mm, codigo_barra)

    # --- Espacio de Validación (Firma y Sello) ---
    val_top = barcode_top - 24 * mm
    
    # Firma a la izquierda
    sig_y = val_top - 12 * mm
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setLineWidth(1)
    c.line(MARGIN + 10 * mm, sig_y, MARGIN + 70 * mm, sig_y)
    c.setFont("Helvetica", 9)
    c.setFillColor(TEXT)
    c.drawString(MARGIN + 20 * mm, sig_y - 4 * mm, "Firma del cliente")
    
    # Sello a la derecha
    stamp_w = 65 * mm
    stamp_h = 16 * mm
    stamp_x = width - MARGIN - stamp_w - 5 * mm
    stamp_y = val_top - 16 * mm
    rounded_box(stamp_x, stamp_y, stamp_w, stamp_h, stroke=colors.HexColor("#9CA3AF"))
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawString(stamp_x + 4 * mm, stamp_y + stamp_h - 4 * mm, "Espacio para sello o timbrado")
    c.setFont("Helvetica", 7)
    c.drawString(stamp_x + 4 * mm, stamp_y + 3 * mm, "(Indica fecha de pago, caja y cajero)")

    # --- Instrucciones ---
    instr_top = val_top - 20 * mm
    instr_h = 22 * mm
    rounded_box(MARGIN, instr_top - instr_h, width - 2 * MARGIN, instr_h)

    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(PRIMARY)
    c.drawString(MARGIN + 6 * mm, instr_top - 5 * mm, "Instrucciones")

    c.setFillColor(TEXT)
    c.setFont("Helvetica", 9)
    lines = [
        f"• Presentar esta boleta en el {bank_name} para efectuar el pago.",
        "• La boleta es válida hasta la fecha de vencimiento indicada.",
        "• Conserve el talón inferior sellado como comprobante de pago.",
    ]
    yy = instr_top - 10 * mm
    for line in lines:
        c.drawString(MARGIN + 8 * mm, yy, line)
        yy -= 4.5 * mm

    # --- Línea de corte ---
    cut_y = instr_top - instr_h - 6 * mm
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    c.setDash(2, 2)
    c.line(MARGIN, cut_y, width - MARGIN, cut_y)
    c.setDash()

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6B7280"))
    c.drawCentredString(width / 2, cut_y - 4 * mm,
                        "— — — — — — — — — — — —  Corte aquí  — — — — — — — — — — — —")

    # --- Talón para caja ---
    slip_h = 42 * mm
    slip_y = 6 * mm
    rounded_box(MARGIN, slip_y, width - 2 * MARGIN, slip_h)

    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(MARGIN + 6 * mm, slip_y + slip_h - 6 * mm,
                 f"Talón para caja – {bank_name}")
    
    # Identificación Institucional compacta en el talón
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(ACCENT)
    c.drawString(MARGIN + 6 * mm, slip_y + slip_h - 11 * mm, ins_slip_title)

    c.setFillColor(TEXT)
    c.setFont("Helvetica", 9)

    ty = slip_y + slip_h - 17 * mm
    # Left column details
    label_value(MARGIN + 6 * mm, ty, "Juicio N°:", getattr(derecho_fijo, "juicio_n", ""), lw=60)
    label_value(MARGIN + 6 * mm, ty - 5 * mm, f"{account_short}:", f"{account_type_short} Nº {cuenta_corriente_display}", lw=60)
    
    # Mini barcode coordinate
    mini = code128.Code128(codigo_barra, barHeight=10 * mm, barWidth=0.45)
    mini_x = width - MARGIN - mini.width - 6 * mm
    mini_y = slip_y + 24 * mm

    # Carátula envuelta
    caratula = getattr(derecho_fijo, "caratula", "")
    lw_caratula = 60
    text_start_x = MARGIN + 6 * mm + lw_caratula
    max_width_caratula_talon = max(40, mini_x - 5 - text_start_x)

    ty_next = draw_label_value_wrapped(
        x=MARGIN + 6 * mm,
        y=ty - 10 * mm,
        label="Carátula:",
        value=caratula,
        max_width=max_width_caratula_talon,
        lw=lw_caratula,
        font_size=8,
        leading=3 * mm,
        max_lines=2
    )

    # Importe y Validación en el talón
    ty_bottom = slip_y + 4 * mm
    label_value(MARGIN + 6 * mm, ty_bottom, "Importe:", formatear_moneda(total_val), lw=60)

    # Sello y firma compactos en el talón
    # Linea de firma
    c.setStrokeColor(colors.HexColor("#D1D5DB"))
    c.line(MARGIN + 80 * mm, ty_bottom + 1 * mm, MARGIN + 115 * mm, ty_bottom + 1 * mm)
    c.setFont("Helvetica", 7)
    c.drawString(MARGIN + 85 * mm, ty_bottom - 2 * mm, "Firma del cliente")
    
    # Recuadro de sello
    rounded_box(MARGIN + 122 * mm, slip_y + 3 * mm, 45 * mm, 12 * mm, stroke=colors.HexColor("#D1D5DB"))
    c.setFont("Helvetica-Bold", 6)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.drawString(MARGIN + 124 * mm, slip_y + 11 * mm, "Sello del Banco")
    c.setFont("Helvetica", 5.5)
    c.drawString(MARGIN + 124 * mm, slip_y + 6 * mm, "(Fecha, caja y cajero)")

    # draw mini-barcode
    mini.drawOn(c, mini_x, mini_y)
    c.setFont("Helvetica", 7)
    c.setFillColor(colors.HexColor("#4B5563"))
    c.drawRightString(mini_x + mini.width, mini_y - 8, codigo_barra)

    # --- Cerrar PDF correctamente ---
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer