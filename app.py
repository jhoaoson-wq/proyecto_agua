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
    
    # --- ENCABEZADO ---
    pdf.set_fill_color(30, 144, 255) # Azul brillante
    pdf.set_text_color(255, 255, 255) # Texto blanco
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 15, "REPORTE DE CONSUMO DE AGUA", ln=True, align='C', fill=True)
    pdf.ln(10)
    
    # --- CUADRO DE RESUMEN ---
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(240, 240, 240) # Gris claro
    pdf.set_font("helvetica", 'B', 12)
    
    pdf.cell(95, 10, f" Mes: {datos['Mes']}", border=1, fill=True)
    pdf.cell(95, 10, f" Total Recibo: S/ {datos['Total_Recibo']:.2f}", border=1, ln=True, fill=True)
    
    pdf.set_font("helvetica", '', 11)
    pdf.cell(0, 10, f" Factor de distribución: {datos['Factor']:.6f}", border=1, ln=True)
    pdf.ln(10)
    
    # --- TABLA DE DETALLE ---
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_fill_color(200, 220, 255)
    
    pdf.cell(60, 10, " Familia", 1, 0, 'L', fill=True)
    pdf.cell(65, 10, " Consumo (m3)", 1, 0, 'C', fill=True)
    pdf.cell(65, 10, " Importe a Pagar", 1, 1, 'C', fill=True)
    
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
    
    # Leemos la base de datos completa
    data = conn.read(worksheet="Historico", ttl=0)
    
    if not data.empty:
        # 1. Creamos una lista de los meses disponibles (del más reciente al más antiguo)
        lista_periodos = data["Mes"].unique().tolist()
        lista_periodos.reverse() 
        
        periodo_sel = st.selectbox("Seleccione el periodo que desea consultar:", lista_periodos)
        
        # 2. Filtramos los datos del periodo elegido
        df_mes = data[data["Mes"] == periodo_sel].iloc[0]
        
        st.markdown(f"### Resumen de {periodo_sel}")
        
        # 3. Mostramos métricas rápidas en columnas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Recibo", f"S/ {df_mes['Total_Recibo']:.2f}")
        m2.metric("Consumo Gen.", f"{df_mes['Total_Act'] - df_mes['Total_Ant']:.3f} m3")
        m3.metric("Factor", f"{df_mes['Factor']:.4f}")
        
        # 4. Tabla de distribución de ese mes
        f_gabi = df_mes['Gabi_Act'] - df_mes['Gabi_Ant']
        f_papiro = df_mes['Papiro_Act'] - df_mes['Papiro_Ant']
        # Calculamos alibi restando al total los otros dos medidores
        f_total = df_mes['Total_Act'] - df_mes['Total_Ant']
        f_alibi = f_total - (f_gabi + f_papiro)
        
        resumen_mes = {
            "Familia": ["Gabi", "Papiro", "Alibi"],
            "Consumo (m3)": [f_gabi, f_papiro, f_alibi],
            "Pago (S/)": [f_gabi * df_mes['Factor'], f_papiro * df_mes['Factor'], f_alibi * df_mes['Factor']]
        }
        
        st.table(pd.DataFrame(resumen_mes))
        
        # 5. Opción para descargar nuevamente el PDF
        st.subheader("📥 Re-descargar Reporte")
        
        datos_pdf_hist = {
            "Mes": periodo_sel, 
            "Total_Recibo": df_mes['Total_Recibo'], 
            "Factor": df_mes['Factor'],
            "Detalle": [
                {"nombre": "Gabi", "m3": f_gabi, "pago": f_gabi * df_mes['Factor']},
                {"nombre": "Papiro", "m3": f_papiro, "pago": f_papiro * df_mes['Factor']},
                {"nombre": "Alibi", "m3": f_alibi, "pago": f_alibi * df_mes['Factor']}
            ]
        }
        
        try:
            pdf_re_output = crear_pdf(datos_pdf_hist)
            st.download_button(
                label=f"📥 Descargar PDF de {periodo_sel}",
                data=pdf_re_output,
                file_name=f"Recibo_Agua_{periodo_sel.replace(' ', '_')}.pdf",
                mime="application/pdf",
                key=f"dl_{periodo_sel}" # Key única para evitar errores de duplicado
            )
        except Exception as e:
            st.error(f"No se pudo generar el PDF histórico: {e}")

        # Botón para ver la tabla completa por si acaso (oculto en un expander)
        with st.expander("Ver todos los datos técnicos (Tabla Completa)"):
            st.dataframe(data, use_container_width=True)
            
    else:
        st.info("No hay registros históricos para mostrar.")
