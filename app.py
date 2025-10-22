# app.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from io import BytesIO
from pypdf import PdfReader
import docx

# --- Configuración de la Página ---
st.set_page_config(page_title="Generador de Matriz de Responsabilidades", layout="wide")

# --- Título de la Aplicación ---
st.title("Generador Automático de Matriz de Responsabilidades")
st.write("Sube los archivos de actividades, organigrama y entrevistas para generar la matriz final en Excel.")

# --- Manejo Seguro y Definitivo de la Clave API ---
def check_api_key():
    if "GOOGLE_API_KEY" not in st.secrets or not st.secrets["GOOGLE_API_KEY"]:
        st.error("🚨 ¡Error de configuración! La GOOGLE_API_KEY no se ha encontrado en los secrets de Streamlit.")
        st.info("Por favor, ve a la configuración de la app (Settings -> Secrets) y añade tu clave de API de Google.")
        st.stop()
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

check_api_key()

# --- Función para extraer texto de diferentes tipos de archivo ---
def get_text_from_file(uploaded_file):
    text = ""
    try:
        file_name = uploaded_file.name
        if file_name.endswith('.txt'):
            text = uploaded_file.read().decode("utf-8")
        elif file_name.endswith('.pdf'):
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        elif file_name.endswith('.docx'):
            document = docx.Document(uploaded_file)
            for para in document.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        st.error(f"Error al leer el archivo {uploaded_file.name}: {e}")
        return None
    return text

# --- Interfaz de la Aplicación ---
with st.container(border=True):
    st.header("Paso 1: Cargar los Documentos Fuente")

    col1, col2 = st.columns(2)
    with col1:
        file_actividades = st.file_uploader(
            "1. Sube el Archivo de Actividades",
            type=["txt", "pdf", "docx"]
        )
        file_organigrama = st.file_uploader(
            "2. Sube el Archivo del Organigrama",
            type=["txt", "pdf", "docx"]
        )
    with col2:
        files_entrevistas = st.file_uploader(
            "3. Sube los Archivos de Entrevistas",
            type=["txt", "pdf", "docx"],
            accept_multiple_files=True
        )

with st.container(border=True):
    st.header("Paso 2: Definir el Prompt y Generar la Matriz")
    
    # CAMBIO: Actualizamos el prompt para que pida un guion '-' en lugar de celdas vacías.
    prompt_base = st.text_area(
        "Prompt para generar la matriz:",
        height=300,
        value="""**Objetivo Principal:**
Crear una matriz de responsabilidades en formato JSON a partir de la información proporcionada. La matriz debe reflejar quién realiza cada actividad basándose exclusivamente en el contenido de las entrevistas.

**Instrucciones Detalladas:**
1. **Analiza los 3 bloques de información que te proporciono a continuación:**
    * **LISTA DE PROCESOS Y ACTIVIDADES:** Este bloque define las filas de la matriz.
    * **ORGANIGRAMA:** Este bloque define los puestos de trabajo que serán las columnas. Ignora los nombres de las personas, usa solo los puestos.
    * **TRANSCRIPCIONES DE ENTREVISTAS:** Esta es tu única fuente de verdad para rellenar la matriz.
2. **Construye la Matriz de la siguiente forma:**
    * La primera columna de la matriz se llamará 'Actividad'.
    * El resto de las columnas serán los nombres de los puestos extraídos del organigrama.
    * Para cada actividad, marca con una 'X' en la columna del puesto correspondiente si la entrevista menciona que ese puesto realiza, participa o es responsable de dicha actividad.
    * Si varios puestos participan en una actividad, marca una 'X' para cada uno de ellos.
    * Procesa únicamente los procesos de negocio existentes mencionados en las entrevistas. No incluyas propuestas de mejora o problemas.
3. **Manejo de Casos Especiales:**
    * Si una actividad de la lista de actividades no es mencionada en ninguna entrevista, rellena toda su fila con guiones '-'.
    * Si en las entrevistas se menciona una actividad importante que NO está en la lista inicial, añádela como una nueva fila.
4. **Formato de Salida Requerido:**
    * **Exclusivamente JSON.**
    * La salida debe ser una lista de objetos JSON. Cada objeto representa una fila (una actividad).
    * Cada objeto debe tener una clave "Actividad" y luego una clave por cada puesto del organigrama. El valor será "X" si el puesto es responsable, o un guion "-" si no lo es.
    * **IMPORTANTE:** No incluyas ningún texto, explicación o comentario en tu respuesta. Solo el código JSON válido."""
    )

    if st.button("Generar Matriz de Responsabilidades", type="primary"):
        if file_actividades and file_organigrama and files_entrevistas:
            with st.spinner("Procesando documentos y generando la matriz con Gemini..."):
                texto_actividades = get_text_from_file(file_actividades)
                texto_organigrama = get_text_from_file(file_organigrama)
                texto_entrevistas = ""
                for file in files_entrevistas:
                    texto_entrevistas += get_text_from_file(file) + "\n\n---\n\n"

                full_prompt = (
                    f"{prompt_base}\n\n"
                    f"--- INICIO LISTA DE PROCESOS Y ACTIVIDADES ---\n{texto_actividades}\n--- FIN LISTA DE PROCESOS Y ACTIVIDADES ---\n\n"
                    f"--- INICIO ORGANIGRAMA ---\n{texto_organigrama}\n--- FIN ORGANIGRAMA ---\n\n"
                    f"--- INICIO TRANSCRIPCIONES DE ENTREVISTAS ---\n{texto_entrevistas}\n--- FIN TRANSCRIPCIONES DE ENTREVISTAS ---"
                )

                try:
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    response = model.generate_content(full_prompt)
                    
                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    json_data = json.loads(cleaned_response)
                    
                    df_matriz = pd.DataFrame(json_data)
                    
                    # CAMBIO: Aseguramos que cualquier celda vacía o nula se rellene con un guion.
                    # Esto hace que el resultado sea robusto incluso si la IA olvida poner un guion.
                    df_matriz.fillna('-', inplace=True)
                    df_matriz.replace('', '-', inplace=True) # Adicional para strings vacíos
                    
                    st.session_state['df_matriz'] = df_matriz
                    st.success("¡Matriz de Responsabilidades generada con éxito!")
                    st.dataframe(df_matriz)

                except Exception as e:
                    st.error(f"Ocurrió un error al generar la matriz: {e}")
                    st.error(f"Respuesta recibida del modelo: {response.text if 'response' in locals() else 'No response'}")
        else:
            st.warning("Por favor, asegúrate de subir todos los archivos requeridos en el Paso 1.")

# --- Descarga del Archivo Excel ---
if 'df_matriz' in st.session_state:
    st.header("Paso 3: Descargar la Matriz")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state['df_matriz'].to_excel(writer, sheet_name='Matriz_Responsabilidades', index=False)
    
    st.download_button(
        label="📥 Descargar Matriz en Excel",
        data=output.getvalue(),
        file_name="matriz_responsabilidades.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
