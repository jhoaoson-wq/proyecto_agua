import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF

# Configuración de la página para móvil
st.set_page_config(page_title="Control de Agua Familiar", layout="centered")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# --- FUNCIÓN PARA GENERAR EL PDF ---
def crear_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    
    # --- ENCABEZADO PRINCIPAL ---
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, "CÁLCULO DE RECIBO DE AGUA", ln=True, align='C')
    pdf.set_font("helvetica", '', 12)
    pdf.cell(0, 10, "Reporte Mensual de Distribución", ln=True, align='C')
    pdf.ln(5)
    
    # --- RESUMEN DE PAGOS Y FECHAS ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", 'B', 11)
    
    # Bloque de Total y Fechas (Simulando la estructura del PDF original)
    pdf.cell(95, 10, f" TOTAL A PAGAR RECIBO: S/ {datos['Total_Recibo']:.2f}", border=1, fill=True)
    pdf.cell(95, 10, f" FECHA DE LECTURA: {datos['Fecha_Lectura']}", border=1, ln=True, fill=True)
    pdf.cell(95, 10, f" FECHA VENCIMIENTO: {datos['Fecha_Vencimiento']}", border=1)
    pdf.cell(95, 10, f" FECHA PROG. PAGO: {datos['Fecha_Pago']}", border=1, ln=True)
    pdf.ln(10)
    
    # --- SECCIÓN 1: DETALLE DE CONSUMOS (m3) ---
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "DETALLE DE CONSUMOS (m3)", ln=True)
    
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(50, 10, " DESCRIPCIÓN", 1, 0, 'L', fill=True)
    pdf.cell(45, 10, " L. ACTUAL", 1, 0, 'C', fill=True)
    pdf.cell(45, 10, " L. ANTERIOR", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, " CONSUMO MES", 1, 1, 'C', fill=True)
    
    pdf.set_font("helvetica", '', 10)
    # Filas de consumos
    familias = [
        ("GABI", datos['G_Act'], datos['G_Ant'], datos['G_Cons']),
        ("PAPIRO", datos['P_Act'], datos['P_Ant'], datos['P_Cons']),
        ("ALIBI (Diferencial)", "-", "-", datos['A_Cons']),
    ]
    
    for nom, act, ant, cons in familias:
        pdf.cell(50, 10, f" {nom}", 1)
        pdf.cell(45, 10, f"{act}" if isinstance(act, str) else f"{act:.3f}", 1, 0, 'C')
        pdf.cell(45, 10, f"{ant}" if isinstance(ant, str) else f"{ant:.3f}", 1, 0, 'C')
        pdf.cell(50, 10, f"{cons:.3f}", 1, 1, 'C')
        
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(140, 10, " CONSUMO TOTAL GENERAL", 1, 0, 'L', fill=True)
    pdf.cell(50, 10, f"{datos['T_Cons']:.3f}", 1, 1, 'C', fill=True)
    pdf.ln(10)
    
    # --- SECCIÓN 2: DISTRIBUCIÓN DE PAGOS ---
    pdf.set_font("helvetica", 'B', 12)
    pdf.cell(0, 10, "DISTRIBUCIÓN DE PAGOS", ln=True)
    
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(50, 10, " FAMILIA", 1, 0, 'L', fill=True)
    pdf.cell(45, 10, " CONSUMO (m3)", 1, 0, 'C', fill=True)
    pdf.cell(45, 10, " FACTOR", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, " SUBTOTAL (S/)", 1, 1, 'C', fill=True)
    
    pdf.set_font("helvetica", '', 10)
    for nom, cons, pago in [("GABI", datos['G_Cons'], datos['G_Pago']), 
                            ("PAPIRO", datos['P_Cons'], datos['P_Pago']), 
                            ("ALIBI", datos['A_Cons'], datos['A_Pago'])]:
        pdf.cell(50, 10, f" {nom}", 1)
        pdf.cell(45, 10, f"{cons:.3f}", 1, 0, 'C')
        pdf.cell(45, 10, f"{datos['Factor']:.4f}", 1, 0, 'C')
        pdf.cell(50, 10, f"S/ {pago:.2f}", 1, 1, 'C')
        
    pdf.set_font("helvetica", 'B', 10)
    pdf.cell(140, 10, " TOTAL A RECAUDAR:", 1, 0, 'R', fill=True)
    pdf.cell(50, 10, f"S/ {datos['Total_Recibo']:.2f}", 1, 1, 'C', fill=True)
    
    return bytes(pdf.output())

def get_last_month_data():
    try:
        # Forzamos ttl=0 para que siempre traiga lo más reciente del Excel
        df = conn.read(worksheet="Historico", ttl=0)
        if not df.empty:
            return df.iloc[-1]
    except:
        return None
    return None

st.title("🚰 Control de Agua")

menu = st.sidebar.selectbox("Menú", ["Ingresar Nuevo Mes", "Ver Históricos"])

if menu == "Ingresar Nuevo Mes":
    st.header("📍 Registro de Periodo")

    with st.expander("1. Datos del Recibo General", expanded=True):
        # --- MODIFICACIÓN: DESPLEGABLES PARA MES Y AÑO ---
        col_m, col_a = st.columns(2)
        meses_lista = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                       "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        mes_nombre = col_m.selectbox("Seleccione Mes", meses_lista, index=datetime.now().month - 1)
        anio_valor = col_a.selectbox("Seleccione Año", [2025, 2026, 2027, 2028], index=1)
        
        mes_final = f"{mes_nombre} {anio_valor}"
        
        importe_total = st.number_input("Importe Total del Recibo (S/.)", min_value=0.0, step=0.10)
        
        col1, col2 = st.columns(2)
        f_venc = col1.date_input("Fecha Vencimiento", format="DD/MM/YYYY")
        f_lect = col2.date_input("Fecha de Lectura", format="DD/MM/YYYY")
        f_pago = st.date_input("Fecha Programada de Pago", format="DD/MM/YYYY")

    # Obtener datos anteriores para autocompletar
    ultimo_registro = get_last_month_data()

    st.subheader("2. Lecturas de Medidores")
    col_g, col_p = st.columns(2)
    
    with col_g:
        st.markdown("**GABI**")
        g_act = st.number_input("Lectura Actual Gabi", format="%.3f", min_value=0.0)
        # --- MODIFICACIÓN: CARGA AUTOMÁTICA DE ANTERIOR ---
        g_ant_val = float(ultimo_registro["Gabi_Act"]) if ultimo_registro is not None else 0.0
        g_ant = st.number_input("Lectura Anterior Gabi", value=g_ant_val, format="%.3f")

    with col_p:
        st.markdown("**PAPIRO**")
        p_act = st.number_input("Lectura Actual Papiro", format="%.3f", min_value=0.0)
        # --- MODIFICACIÓN: CARGA AUTOMÁTICA DE ANTERIOR ---
        p_ant_val = float(ultimo_registro["Papiro_Act"]) if ultimo_registro is not None else 0.0
        p_ant = st.number_input("Lectura Anterior Papiro", value=p_ant_val, format="%.3f")

    st.markdown("---")
    st.markdown("**CONSUMO GENERAL**")
    t_act = st.number_input("Lectura Actual General", format="%.3f", min_value=0.0)
    # --- MODIFICACIÓN: CARGA AUTOMÁTICA DE ANTERIOR ---
    t_ant_val = float(ultimo_registro["Total_Act"]) if ultimo_registro is not None else 0.0
    t_ant = st.number_input("Lectura Anterior General", value=t_ant_val, format="%.3f")

    if t_act > t_ant and importe_total > 0:
        cons_total = t_act - t_ant
        factor = importe_total / cons_total

        c_gabi = g_act - g_ant
        c_papiro = p_act - p_ant
        c_alibi = cons_total - (c_gabi + c_papiro)

        if st.button("✅ Verificar y Calcular"):
            st.subheader("Resumen de Distribución")
            resumen_data = {
                "Familia": ["Gabi", "Papiro", "Alibi"],
                "Consumo (m3)": [c_gabi, c_papiro, c_alibi],
                "Pago (S/)": [c_gabi * factor, c_papiro * factor, c_alibi * factor]
            }
            df_resumen = pd.DataFrame(resumen_data)
            st.table(df_resumen)
            
            # Preparar datos para guardar
            new_data = pd.DataFrame([{
                "Mes": mes_final, "Total_Recibo": importe_total,
                "Vencimiento": str(f_venc), "Lectura": str(f_lect), "Pago": str(f_pago),
                "Gabi_Act": g_act, "Gabi_Ant": g_ant,
                "Papiro_Act": p_act, "Papiro_Ant": p_ant,
                "Total_Act": t_act, "Total_Ant": t_ant, "Factor": factor
            }])

            # --- MODIFICACIÓN: GUARDADO ACUMULATIVO ---
            try:
                existing_data = conn.read(worksheet="Historico", ttl=0)
                updated_df = pd.concat([existing_data, new_data], ignore_index=True)
                conn.update(worksheet="Historico", data=updated_df)
                st.success(f"💾 ¡Datos de {mes_final} guardados exitosamente!")
            except Exception as e:
                st.error(f"Error al guardar en Sheets: {e}")

            # GENERAR PDF
            datos_pdf = {
                "Mes": mes_final, 
                "Total_Recibo": importe_total, 
                "Factor": factor,
                "Detalle": [
                    {"nombre": "Gabi", "m3": c_gabi, "pago": c_gabi*factor},
                    {"nombre": "Papiro", "m3": c_papiro, "pago": c_papiro*factor},
                    {"nombre": "Alibi", "m3": c_alibi, "pago": c_alibi*factor}
                ]
            }
            
            try:
                pdf_output = crear_pdf(datos_pdf)
                st.download_button(
                    label="📥 Descargar Reporte PDF",
                    data=pdf_output,
                    file_name=f"Recibo_Agua_{mes_final.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="download-pdf"
                )
            except Exception as e:
                st.error(f"Error al generar el PDF: {e}")

            # Botón WhatsApp
            texto_wa = f"Hola! El recibo de agua de {mes_final} ya está listo. Total: S/. {importe_total:.2f}."
            url_wa = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
            st.link_button("📲 Notificar por WhatsApp", url_wa)
    else:
        if importe_total > 0:
            st.warning("⚠️ La lectura actual general debe ser mayor a la anterior.")

elif menu == "Ver Históricos":
    st.header("📅 Consulta de Historial")
    data = conn.read(worksheet="Historico", ttl=0)
    
    if not data.empty:
        lista_periodos = data["Mes"].unique().tolist()
        lista_periodos.reverse() 
        periodo_sel = st.selectbox("Seleccione el periodo:", lista_periodos)
        
        df_mes = data[data["Mes"] == periodo_sel].iloc[0]
        
        # --- CÁLCULOS PARA MOSTRAR EN PANTALLA ---
        g_cons = df_mes['Gabi_Act'] - df_mes['Gabi_Ant']
        p_cons = df_mes['Papiro_Act'] - df_mes['Papiro_Ant']
        t_cons = df_mes['Total_Act'] - df_mes['Total_Ant']
        a_cons = t_cons - (g_cons + p_cons)

        st.markdown(f"### 📄 Resumen de {periodo_sel}")
        
        # Métricas principales resaltadas
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Recibo", f"S/ {df_mes['Total_Recibo']:.2f}")
        c2.metric("Factor", f"{df_mes['Factor']:.6f}")
        c3.metric("Consumo Total", f"{t_cons:.3f} m³")

        # --- NUEVA TABLA DE CONSUMOS (Como en el reporte detallado) ---
        st.subheader("🔍 Detalle de Consumos")
        consumo_table = pd.DataFrame({
            "Descripción": ["GABI", "PAPIRO", "ALIBI (Dif.)", "TOTAL GENERAL"],
            "L. Actual": [df_mes['Gabi_Act'], df_mes['Papiro_Act'], "-", df_mes['Total_Act']],
            "L. Anterior": [df_mes['Gabi_Ant'], df_mes['Papiro_Ant'], "-", df_mes['Total_Ant']],
            "Consumo (m³)": [g_cons, p_cons, a_cons, t_cons]
        })
        st.table(consumo_table)

        # --- NUEVA TABLA DE PAGOS ---
        st.subheader("💰 Distribución de Pagos")
        pagos_table = pd.DataFrame({
            "Familia": ["GABI", "PAPIRO", "ALIBI"],
            "m³": [g_cons, p_cons, a_cons],
            "Subtotal": [f"S/ {g_cons * df_mes['Factor']:.2f}", 
                         f"S/ {p_cons * df_mes['Factor']:.2f}", 
                         f"S/ {a_cons * df_mes['Factor']:.2f}"]
        })
        st.table(pagos_table)

        # --- BOTÓN DE DESCARGA PDF ---
        # (Aquí usamos el mismo 'datos_pdf_hist' que definimos antes)
        datos_pdf_hist = {
            "Mes": periodo_sel, "Total_Recibo": df_mes['Total_Recibo'],
            "Fecha_Lectura": df_mes['Lectura'], "Fecha_Vencimiento": df_mes['Vencimiento'],
            "Fecha_Pago": df_mes['Pago'], "Factor": df_mes['Factor'],
            "G_Act": df_mes['Gabi_Act'], "G_Ant": df_mes['Gabi_Ant'], "G_Cons": g_cons,
            "P_Act": df_mes['Papiro_Act'], "P_Ant": df_mes['Papiro_Ant'], "P_Cons": p_cons,
            "T_Act": df_mes['Total_Act'], "T_Ant": df_mes['Total_Ant'], "T_Cons": t_cons,
            "A_Cons": a_cons, "G_Pago": g_cons * df_mes['Factor'],
            "P_Pago": p_cons * df_mes['Factor'], "A_Pago": a_cons * df_mes['Factor']
        }

        try:
            pdf_re_output = crear_pdf(datos_pdf_hist)
            st.download_button(
                label=f"📥 Descargar PDF Completo de {periodo_sel}",
                data=pdf_re_output,
                file_name=f"Recibo_Agua_{periodo_sel.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"dl_{periodo_sel}"
            )
        except Exception as e:
            st.error(f"Error al generar el PDF: {e}")

        with st.expander("Ver fechas del periodo"):
            st.write(f"**Lectura:** {df_mes['Lectura']}")
            st.write(f"**Vencimiento:** {df_mes['Vencimiento']}")
            st.write(f"**Pago Programado:** {df_mes['Pago']}")

        # Botón para ver la tabla completa por si acaso (oculto en un expander)
        with st.expander("Ver todos los datos técnicos (Tabla Completa)"):
            st.dataframe(data, use_container_width=True)
            
    else:
        st.info("No hay registros históricos para mostrar.")
