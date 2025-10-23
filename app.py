# app.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from io import BytesIO
from pypdf import PdfReader
import docx
from PIL import Image

# --- Configuración de la Página ---
st.set_page_config(page_title="Analizador de Procesos", layout="wide")

# --- Título de la Aplicación ---
st.title("Herramienta de Análisis y Diagnóstico de Procesos")
st.write("Genera una lista de actividades a partir de entrevistas y luego crea una Matriz PUO de diagnóstico.")

# --- Manejo Seguro de la Clave API ---
def check_api_key():
    if "GOOGLE_API_KEY" not in st.secrets or not st.secrets["GOOGLE_API_KEY"]:
        st.error("🚨 ¡Error de configuración! La GOOGLE_API_KEY no se ha encontrado en los secrets de Streamlit.")
        st.info("Por favor, ve a la configuración de la app (Settings -> Secrets) y añade tu clave de API de Google.")
        st.stop()
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

check_api_key()

# --- Función para extraer contenido de diferentes archivos ---
def get_content_from_file(uploaded_file):
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith(('.png', '.jpg', '.jpeg')):
            return Image.open(uploaded_file)
        elif file_name.endswith('.txt'):
            return uploaded_file.read().decode("utf-8")
        elif file_name.endswith('.pdf'):
            text = ""
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages: text += page.extract_text() or ""
            return text
        elif file_name.endswith('.docx'):
            text = ""
            document = docx.Document(uploaded_file)
            for para in document.paragraphs: text += para.text + "\n"
            return text
        elif file_name.endswith(('.xlsx', '.xls', '.csv')):
            df = pd.read_excel(uploaded_file) if file_name.endswith(('.xlsx', '.xls')) else pd.read_csv(uploaded_file)
            return df.to_string()
    except Exception as e:
        st.error(f"Error al leer el archivo {uploaded_file.name}: {e}")
    return None

# --- Prompt Fijo para el Paso 1 (Rellenado con tu prompt) ---
prompt_actividades = """Analiza todas las transcripciones de entrevistas proporcionadas.
Identifica y lista todos los procesos de negocio mencionados.

IMPORTANTE: SOLO PROCESOS DE NEGOCIO DE LA EMPRESA EXISTENTES. NO PROPUESTAS DE MEJORA O PROBLEMAS MENCIONADOS.
Para cada proceso, detalla las actividades específicas asociadas a él que se realizan actualmente. Ignora cualquier sugerencia de mejora o problemas, céntrate solo en las actividades que sí se hacen.

El objetivo es crear una lista maestra de todas las actividades de la empresa, agrupadas por su proceso principal. La primera actividad de cada proceso debe ser la que lo inicia y la última con la que se finaliza.
No debes añadir nombres de las personas.

IMPORTANTE: Ordena los procesos y actividades según el orden de la cadena de valor de la empresa, y al final, los procesos transversales (administración, finanzas, etc.).

**Formato de Salida Requerido:**
*   **Exclusivamente JSON.**
*   La salida debe ser una lista de objetos JSON.
*   Cada objeto representa una actividad y debe tener tres claves: "Proceso", "Número", y "Grandes actividades del proceso".
*   Repite el nombre del proceso en la clave "Proceso" para cada actividad que le pertenezca.
*   La clave "Número" debe ser una secuencia numérica continua.
*   No incluyas ninguna explicación adicional, solo el resultado JSON."""

# --- Interfaz de la Aplicación ---

# --- PASO 1: GENERAR LISTA DE ACTIVIDADES ---
with st.container(border=True):
    st.header("Paso 1: Generar la Lista de Actividades a partir de Entrevistas")
    
    files_entrevistas = st.file_uploader(
        "Sube uno o más archivos de entrevistas (.txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True
    )

    if st.button("Generar Lista de Actividades", type="primary"):
        if files_entrevistas:
            with st.spinner("Analizando entrevistas y generando la lista..."):
                texto_entrevistas = ""
                for file in files_entrevistas:
                    texto_entrevistas += get_content_from_file(file) + "\n\n---\n\n"
                
                st.session_state['texto_entrevistas'] = texto_entrevistas

                full_prompt = f"{prompt_actividades}\n\n--- INICIO ENTREVISTAS ---\n{texto_entrevistas}\n--- FIN ENTREVISTAS ---"
                
                try:
                    # CORRECCIÓN 1: Usamos el nombre de modelo estándar
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(full_prompt)
                    
                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    json_data = json.loads(cleaned_response)
                    df_resultado = pd.DataFrame(json_data)
                    
                    st.session_state['df_actividades'] = df_resultado
                    st.success("¡Lista de actividades generada con éxito!")
                    st.dataframe(df_resultado)

                except Exception as e:
                    st.error(f"Ocurrió un error al generar la lista: {e}")

# --- PASO 2: GENERAR MATRIZ PUO ---
if 'df_actividades' in st.session_state:
    with st.container(border=True):
        st.header("Paso 2: Generar la Matriz PUO (Problema-Usuario-Objetivo)")
        st.write("Ahora, basándonos en las entrevistas y la lista de actividades generada, crearemos la matriz de diagnóstico.")
        
        file_organigrama = st.file_uploader(
            "Sube el organigrama (Opcional)",
            type=["jpg", "jpeg", "png", "pdf", "docx", "txt", "xlsx", "xls", "csv"]
        )

        prompt_puo = st.text_area(
            "Prompt para generar la Matriz PUO:",
            height=200,
            value="""Basándote en las entrevistas y la lista de actividades proporcionada, crea una Matriz PUO en formato JSON.

Para cada actividad de la lista, analiza las entrevistas para:
1.  **Identificar un Problema:** ¿Qué dificultad, ineficiencia o dolor se menciona en relación a esa actividad? Si no se menciona ninguno, déjalo en blanco.
2.  **Identificar el Usuario Afectado:** ¿Qué rol o puesto (según el organigrama si se proporciona, o las entrevistas si no) sufre más por este problema?
3.  **Definir un Objetivo:** Propón un objetivo claro y medible para solucionar el problema.

**Formato de Salida:**
*   **Exclusivamente JSON.**
*   Una lista de objetos, donde cada objeto tiene las claves: "Actividad", "Problema Detectado", "Usuario Afectado", "Objetivo de Mejora"."""
        )

        if st.button("Generar Matriz PUO", type="primary"):
            with st.spinner("Creando la Matriz PUO..."):
                texto_entrevistas = st.session_state['texto_entrevistas']
                actividades_json = st.session_state['df_actividades'].to_json(orient='records')
                
                prompt_parts = [
                    prompt_puo,
                    "\n\n--- LISTA DE ACTIVIDADES BASE ---\n",
                    actividades_json,
                    "\n\n--- TRANSCRIPCIONES DE ENTREVISTAS ---\n",
                    texto_entrevistas
                ]

                if file_organigrama:
                    contenido_organigrama = get_content_from_file(file_organigrama)
                    if contenido_organigrama:
                        prompt_parts.append("\n\n--- ORGANIGRAMA DE REFERENCIA ---\n")
                        prompt_parts.append(contenido_organigrama)

                try:
                    # CORRECCIÓN 2: Usamos el nombre de modelo correcto aquí también
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt_parts)

                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    json_data = json.loads(cleaned_response)
                    df_puo = pd.DataFrame(json_data)

                    st.session_state['df_puo'] = df_puo
                    st.success("¡Matriz PUO generada con éxito!")
                    st.dataframe(df_puo)

                except Exception as e:
                    st.error(f"Ocurrió un error al generar la Matriz PUO: {e}")

# --- PASO 3: DESCARGA ---
if 'df_actividades' in st.session_state and 'df_puo' in st.session_state:
    with st.container(border=True):
        st.header("Paso 3: Descargar Resultados")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state['df_actividades'].to_excel(writer, sheet_name='Lista_Actividades', index=False)
            st.session_state['df_puo'].to_excel(writer, sheet_name='Matriz_PUO', index=False)
        
        st.download_button(
            label="📥 Descargar Análisis Completo en Excel",
            data=output.getvalue(),
            file_name="analisis_de_procesos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
