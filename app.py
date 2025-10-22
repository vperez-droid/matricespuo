# app.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from io import BytesIO

# CAMBIO: Importamos las nuevas bibliotecas para leer PDF y DOCX
from pypdf import PdfReader
import docx

# --- Configuración de la Página ---
st.set_page_config(page_title="Generador de Matrices con Gemini", layout="wide")

# --- Título de la Aplicación ---
st.title("Generador Automático de Matrices con Gemini Flash")
st.write("Sube transcripciones de entrevistas para generar una matriz de diagnóstico y luego una matriz PUO.")

# --- Manejo Seguro y Definitivo de la Clave API ---
def check_api_key():
    if "GOOGLE_API_KEY" not in st.secrets or not st.secrets["GOOGLE_API_KEY"]:
        st.error("🚨 ¡Error de configuración! La GOOGLE_API_KEY no se ha encontrado en los secrets de Streamlit.")
        st.info("Por favor, ve a la configuración de la app (Settings -> Secrets) y añade tu clave de API de Google para que la aplicación funcione.")
        st.stop()
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

check_api_key()

# CAMBIO: Creamos una función para extraer texto de diferentes tipos de archivo
def get_text_from_file(uploaded_file):
    """
    Extrae el texto de un archivo subido (txt, pdf, docx).
    """
    text = ""
    try:
        file_name = uploaded_file.name
        if file_name.endswith('.txt'):
            # Lee el archivo de texto como bytes y lo decodifica
            text = uploaded_file.read().decode("utf-8")
        elif file_name.endswith('.pdf'):
            # Lee el archivo PDF
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
        elif file_name.endswith('.docx'):
            # Lee el archivo Word
            document = docx.Document(uploaded_file)
            for para in document.paragraphs:
                text += para.text + "\n"
    except Exception as e:
        st.error(f"Error al leer el archivo {uploaded_file.name}: {e}")
        return None
    return text

# --- Paso 1: Matriz de Diagnóstico ---
with st.container(border=True):
    st.header("Paso 1: Cargar Entrevistas y Generar Matriz de Diagnóstico")

    # CAMBIO: Actualizamos los tipos de archivo permitidos en el uploader
    uploaded_files = st.file_uploader(
        "Sube las transcripciones (archivos .txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True
    )

    prompt_diagnostico = st.text_area(
        "Prompt para generar la Matriz de Diagnóstico:",
        height=150,
        value="A partir de las siguientes entrevistas, extrae los principales procesos, actividades y problemas mencionados. Organiza la información en un formato JSON con una lista de objetos, donde cada objeto tenga las claves: 'Proceso', 'Actividad', 'Problema'. Asegúrate de que la respuesta sea únicamente el código JSON válido y nada más."
    )

    if st.button("Generar Matriz de Diagnóstico"):
        if uploaded_files and prompt_diagnostico:
            with st.spinner("Procesando entrevistas con Gemini Flash..."):
                all_text = ""
                # CAMBIO: Usamos nuestra nueva función para leer cada archivo
                for uploaded_file in uploaded_files:
                    st.write(f"Leyendo archivo: {uploaded_file.name}...")
                    extracted_text = get_text_from_file(uploaded_file)
                    if extracted_text:
                        all_text += extracted_text + "\n\n---\n\n" # Separador entre documentos
                
                if all_text:
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        full_prompt = f"{prompt_diagnostico}\n\nEntrevistas:\n{all_text}"
                        
                        response = model.generate_content(full_prompt)
                        
                        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                        json_response = json.loads(cleaned_response)
                        df_diagnostico = pd.DataFrame(json_response)
                        
                        st.session_state['df_diagnostico'] = df_diagnostico
                        st.success("Matriz de Diagnóstico generada con éxito.")
                        st.dataframe(df_diagnostico)

                    except Exception as e:
                        st.error(f"Ocurrió un error al generar la matriz de diagnóstico: {e}")
                        st.error(f"Respuesta recibida del modelo: {response.text if 'response' in locals() else 'No response'}")
        else:
            st.warning("Asegúrate de subir al menos un archivo y de que el prompt no esté vacío.")

# ... El resto del código para el Paso 2 y la descarga permanece exactamente igual ...
# --- Paso 2: Matriz PUO ---
with st.container(border=True):
    st.header("Paso 2: Generar Matriz PUO")

    if 'df_diagnostico' in st.session_state:
        st.write("A partir de la siguiente Matriz de Diagnóstico:")
        st.dataframe(st.session_state['df_diagnostico'], use_container_width=True)
        
        prompt_puo = st.text_area(
            "Prompt para generar la Matriz PUO:",
            height=150,
            value="A partir de la siguiente matriz de diagnóstico en formato JSON, crea una matriz PUO. Identifica el problema principal, el usuario afectado y define un objetivo claro de mejora. Devuelve el resultado en un formato JSON con una lista de objetos, donde cada objeto tenga las claves: 'Problema', 'Usuario Afectado', 'Objetivo de Mejora'. Asegúrate de que la respuesta sea únicamente el código JSON válido."
        )

        if st.button("Generar Matriz PUO"):
            if prompt_puo:
                with st.spinner("Generando la matriz PUO con Gemini Flash..."):
                    diagnostico_json = st.session_state['df_diagnostico'].to_json(orient='records')
                    
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        full_prompt_puo = f"{prompt_puo}\n\nMatriz de Diagnóstico:\n{diagnostico_json}"
                        
                        response = model.generate_content(full_prompt_puo)
                        
                        cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                        json_response_puo = json.loads(cleaned_response)
                        df_puo = pd.DataFrame(json_response_puo)
                        
                        st.session_state['df_puo'] = df_puo
                        st.success("Matriz PUO generada con éxito.")
                        st.dataframe(df_puo)

                    except Exception as e:
                        st.error(f"Ocurrió un error al generar la matriz PUO: {e}")
                        st.error(f"Respuesta recibida del modelo: {response.text if 'response' in locals() else 'No response'}")
            else:
                st.warning("Asegúrate de que el prompt para la matriz PUO no esté vacío.")

# --- Descarga del Archivo Excel ---
if 'df_diagnostico' in st.session_state and 'df_puo' in st.session_state:
    st.header("Paso 3: Descargar Resultados")
    
    out
