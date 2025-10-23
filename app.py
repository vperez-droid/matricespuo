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
st.write("Genera una lista de actividades a partir de entrevistas y luego crea una Matriz de Responsabilidades.")

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

# --- Prompt Fijo para el Paso 1 ---
prompt_actividades = """
**Objetivo:** Extraer una lista de actividades detalladas a partir de las transcripciones de las entrevistas y formatearlas en una estructura JSON.

**Instrucciones Estrictas:**
1.  **Analiza el texto de las entrevistas** que te proporciono a continuación.
2.  **Identifica cada tarea o actividad individual** que se menciona.
3.  **Crea un objeto JSON para cada actividad.**
4.  Cada objeto JSON debe tener TRES claves obligatorias:
    *   `"Proceso"`: El proceso de negocio general al que pertenece la actividad (ej: "Captación de Clientes", "Proceso Judicial", "Facturación").
    *   `"Número"`: Un número secuencial para la actividad, empezando en 1.
    *   `"Grandes actividades del proceso"`: La descripción específica de la tarea (ej: "Revisar el correo electrónico", "Presentar la demanda", "Emitir facturas").

**Formato de Salida Obligatorio:**
*   Tu respuesta debe ser **EXCLUSIVAMENTE un array JSON válido** que contenga los objetos.
*   No incluyas texto introductorio, explicaciones, ni la palabra "json" o las marcas ```.
*   La salida debe empezar con `[` y terminar con `]`.
"""

# --- Prompt Fijo para el Paso 2 ---
prompt_responsabilidades = """
**Objetivo Principal:**
Crear una matriz de responsabilidades en formato JSON. Debes usar la lista de actividades proporcionada como base y rellenarla usando la información de las entrevistas.

**Bloques de Información que Analizarás:**
1.  **LISTA DE ACTIVIDADES:** Contiene las filas base de la matriz con las columnas "Proceso", "Número" y "Grandes actividades del proceso". Debes mantener estas columnas en tu salida.
2.  **ENTREVISTAS:** Es tu única fuente de verdad para identificar quién hace qué.
3.  **ORGANIGRAMA (Opcional):** Puedes usarlo como referencia para confirmar puestos de trabajo.

**Instrucciones Detalladas:**
1.  **Identifica las Columnas de Puestos:**
    *   Lee las entrevistas e identifica todos los puestos de trabajo y las personas asociadas.
    *   El nombre de cada nueva columna en tu matriz debe seguir el formato: 'Puesto (Nombre Persona)'. Por ejemplo, 'Director Comercial (Juan Pérez)'.
    *   Si un puesto es mencionado sin un nombre, usa solo el 'Puesto'.
2.  **Construye la Matriz de Salida:**
    *   Tu JSON de salida debe ser una lista de objetos.
    *   Cada objeto debe PRESERVAR las claves originales ("Proceso", "Número", "Grandes actividades del proceso") de la lista de actividades que te he pasado.
    *   Añade a cada objeto las nuevas claves para cada 'Puesto (Nombre Persona)' que hayas identificado. Solo deben aparecer las personas a las que se hizo la entrevista.
3.  **Asignación de Responsabilidades:**
    *   Para cada actividad, marca con una 'X' en la columna del puesto correspondiente si la entrevista menciona que esa persona/puesto realiza la tarea.
    *   Si un puesto no tiene nada que ver con una actividad, el valor debe ser un guion ('-').
    *   Si varios puestos participan en una actividad, marca una 'X' para CADA UNO de ellos.

**Formato de Salida Requerido:**
*   **Exclusivamente JSON.** No incluyas explicaciones ni texto adicional.
*   El JSON debe ser una lista de objetos, donde cada objeto es una fila completa de la matriz.
"""


# --- Interfaz de la Aplicación ---

# --- PASO 1: GENERAR LISTA DE ACTIVIDADES ---
with st.container(border=True):
    st.header("Paso 1: Generar la Lista de Actividades a partir de Entrevistas")
    
    files_entrevistas = st.file_uploader(
        "Sube uno o más archivos de entrevistas",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True
    )

    if st.button("Generar Lista de Actividades", type="primary"):
        if files_entrevistas:
            with st.spinner("Analizando entrevistas y generando la lista..."):
                texto_entrevistas = ""
                for file in files_entrevistas:
                    content = get_content_from_file(file)
                    if content: texto_entrevistas += content + "\n\n---\n\n"
                
                st.session_state['texto_entrevistas'] = texto_entrevistas
                
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(f"{prompt_actividades}\n\n--- ENTREVISTAS ---\n{texto_entrevistas}")
                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    
                    if not cleaned_response:
                        st.error("Error: El modelo devolvió una respuesta vacía.")
                    else:
                        # --- INICIO DEL BLOQUE SEGURO ---
                        # Todo el código que depende de una respuesta válida va aquí dentro.
                        json_data = json.loads(cleaned_response)
                        df_actividades = pd.DataFrame(json_data)
                        
                        # Re-numerar la columna 'Número' para que sea continua
                        df_actividades['Número'] = df_actividades.index + 1
                        
                        # Guardar en la sesión y mostrar al usuario
                        st.session_state['df_actividades'] = df_actividades
                        st.success("¡Paso 1 completado! Lista de actividades generada.")
                        st.dataframe(df_actividades)
                        # --- FIN DEL BLOQUE SEGURO ---

                except json.JSONDecodeError as e:
                    st.error(f"Error al procesar el JSON: {e}")
                    st.error("La respuesta del modelo no es un JSON válido.")
                except Exception as e: 
                    st.error(f"Ocurrió un error inesperado en el Paso 1: {e}")
        else: 
            st.warning("Por favor, sube al menos un archivo de entrevista.")


# --- PASO 2: GENERAR MATRIZ DE RESPONSABILIDADES ---
if 'df_actividades' in st.session_state:
    with st.container(border=True):
        st.header("Paso 2: Generar la Matriz de Responsabilidades")
        
        file_organigrama = st.file_uploader(
            "Sube el organigrama (Opcional)",
            type=["jpg", "jpeg", "png", "pdf", "docx", "txt", "xlsx", "xls", "csv"]
        )

        if st.button("Generar Matriz de Responsabilidades", type="primary"):
            with st.spinner("Creando la Matriz de Responsabilidades..."):
                texto_entrevistas = st.session_state['texto_entrevistas']
                actividades_json = st.session_state['df_actividades'].to_json(orient='records')
                
                prompt_parts = [
                    prompt_responsabilidades,
                    "\n\n--- LISTA DE ACTIVIDADES ---\n", actividades_json,
                    "\n\n--- ENTREVISTAS ---\n", texto_entrevistas
                ]

                if file_organigrama:
                    contenido_organigrama = get_content_from_file(file_organigrama)
                    if contenido_organigrama:
                        prompt_parts.extend(["\n\n--- ORGANIGRAMA ---\n", contenido_organigrama])

                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(prompt_parts)

                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    json_data = json.loads(cleaned_response)
                    df_responsabilidades = pd.DataFrame(json_data)
                    df_responsabilidades.fillna('-', inplace=True)

                    st.session_state['df_responsabilidades'] = df_responsabilidades
                    st.success("¡Paso 2 completado! Matriz de responsabilidades generada.")
                    st.dataframe(df_responsabilidades)

                except Exception as e: st.error(f"Ocurrió un error en el Paso 2: {e}")

# --- PASO 3: DESCARGA ---
if 'df_actividades' in st.session_state and 'df_responsabilidades' in st.session_state:
    with st.container(border=True):
        st.header("Paso 3: Descargar Resultados")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state['df_actividades'].to_excel(writer, sheet_name='Lista_Actividades', index=False)
            st.session_state['df_responsabilidades'].to_excel(writer, sheet_name='Matriz_Responsabilidades', index=False)
        
        st.download_button(
            label="📥 Descargar Análisis Completo en Excel",
            data=output.getvalue(),
            file_name="analisis_de_procesos.xlsx",
            mime="application/vnd.openxmlformats-officedocument.sheet"
        )
