import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import urllib.parse
from fpdf import FPDF  # <-- Nueva librería para el PDF

# Configuración de la página para móvil
st.set_page_config(page_title="Control de Agua Familiar", layout="centered")

# Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)


# --- FUNCIÓN PARA GENERAR EL PDF ---
def crear_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    
    # --- ENCABEZADO ---
    pdf.set_fill_color(30, 144, 255) # Azul brillante
    pdf.set_text_color(255, 255, 255) # Texto blanco
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 15, "REPORTE DE CONSUMO DE AGUA", ln=True, align='C', fill=True)
    pdf.ln(10)
    
    # --- CUADRO DE RESUMEN ---
    pdf.set_text_color(0, 0, 0) # Volver a texto negro
    pdf.set_fill_color(240, 240, 240) # Gris claro
    pdf.set_font("helvetica", 'B', 12)
    
    # Fila 1 del resumen
    pdf.cell(95, 10, f" Mes: {datos['Mes']}", border=1, fill=True)
    pdf.cell(95, 10, f" Total Recibo: S/ {datos['Total_Recibo']:.2f}", border=1, ln=True, fill=True)
    
    # Fila 2 del resumen
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 10, f" Factor de distribución: {datos['Factor']:.6f}", border=1, ln=True)
    pdf.ln(10)
    
    # --- TABLA DE DETALLE ---
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_fill_color(200, 220, 255) # Azul muy claro para cabecera
    
    # Cabeceras de tabla
    pdf.cell(60, 10, " Familia", 1, 0, 'L', fill=True)
    pdf.cell(65, 10, " Consumo (m3)", 1, 0, 'C', fill=True)
    pdf.cell(65, 10, " Importe a Pagar", 1, 1, 'C', fill=True)
    
    # Filas de la tabla
    pdf.set_font("helvetica", size=11)
    for fila in datos['Detalle']:
        pdf.cell(60, 10, f" {fila['nombre']}", 1)
        pdf.cell(65, 10, f"{fila['m3']:.3f}", 1, 0, 'C')
        pdf.cell(65, 10, f"S/ {fila['pago']:.2f}", 1, 1, 'C')
        
    pdf.ln(15)
    pdf.set_font("helvetica", 'I', 10)
    pdf.cell(0, 10, "Este es un documento informativo para la distribución familiar.", ln=True, align='C')
    
    return bytes(pdf.output())


def get_last_month_data():
    try:
        df = conn.read(worksheet="Historico")
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
        mes = st.text_input("Mes a informar (Ej: Abril 2026)")
        importe_total = st.number_input("Importe Total del Recibo (S/.)", min_value=0.0)
        col1, col2 = st.columns(2)
        f_venc = col1.date_input("Fecha Vencimiento")
        f_lect = col2.date_input("Fecha de Lectura")
        f_pago = st.date_input("Fecha Programada de Pago")

    ultimo_registro = get_last_month_data()

    st.subheader("2. Lecturas de Medidores")
    col_g, col_p = st.columns(2)
    with col_g:
        st.markdown("**GABI**")
        g_act = st.number_input("Lectura Actual Gabi", format="%.3f")
        g_ant_val = float(ultimo_registro["Gabi_Act"]) if ultimo_registro is not None else 0.0
        g_ant = st.number_input("Lectura Anterior Gabi", value=g_ant_val, format="%.3f")

    with col_p:
        st.markdown("**PAPIRO**")
        p_act = st.number_input("Lectura Actual Papiro", format="%.3f")
        p_ant_val = float(ultimo_registro["Papiro_Act"]) if ultimo_registro is not None else 0.0
        p_ant = st.number_input("Lectura Anterior Papiro", value=p_ant_val, format="%.3f")

    st.markdown("---")
    st.markdown("**CONSUMO GENERAL**")
    t_act = st.number_input("Lectura Actual General", format="%.3f")
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
            st.write(f"**Factor del mes:** {factor:.6f}")

            # BOTÓN PARA GUARDAR
            # Nota: Streamlit necesita manejar el estado para guardar
            new_data = pd.DataFrame([{
                "Mes": mes, "Total_Recibo": importe_total,
                "Vencimiento": str(f_venc), "Lectura": str(f_lect), "Pago": str(f_pago),
                "Gabi_Act": g_act, "Gabi_Ant": g_ant,
                "Papiro_Act": p_act, "Papiro_Ant": p_ant,
                "Total_Act": t_act, "Total_Ant": t_ant, "Factor": factor
            }])

            # Guardar en Google Sheets
            existing_data = conn.read(worksheet="Historico")
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            conn.update(worksheet="Historico", data=updated_df)

            # GENERAR PDF
            datos_pdf = {
                "Mes": mes, 
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
                    file_name=f"Recibo_Agua_{mes.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    key="download-pdf" # Añadimos una clave única
                )
            except Exception as e:
                st.error(f"Error al generar el archivo: {e}")

            # Botón WhatsApp
            texto_wa = f"Hola! El recibo de agua de {mes} ya está listo. Total: S/. {importe_total:.2f}. "
            url_wa = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
            st.link_button("📲 Notificar por WhatsApp", url_wa)

elif menu == "Ver Históricos":
    st.header("📅 Historial de Pagos")
    data = conn.read(worksheet="Historico")
    st.dataframe(data)
