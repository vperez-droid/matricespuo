# app.py

import streamlit as st
import pandas as pd
# CAMBIO: Importamos la librería de Google en lugar de la de OpenAI
import google.generativeai as genai
import json
from io import BytesIO

# --- Configuración de la Página ---
st.set_page_config(page_title="Generador de Matrices con Gemini", layout="wide")

# --- Título de la Aplicación ---
st.title("Generador Automático de Matrices con Gemini Flash")
st.write("Sube transcripciones de entrevistas para generar una matriz de diagnóstico y luego una matriz PUO.")

# --- Manejo Seguro de la Clave API ---
# CAMBIO: Buscamos la clave de API de Google en los secrets
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    st.warning("Clave de API de Google no encontrada. Por favor, ingrésala manualmente para uso local.")
    api_key = st.text_input("Ingresa tu clave de API de Google AI", type="password")

# CAMBIO: Configuramos la API de Google
if api_key:
    genai.configure(api_key=api_key)

# --- Paso 1: Matriz de Diagnóstico ---
with st.container(border=True):
    st.header("Paso 1: Cargar Entrevistas y Generar Matriz de Diagnóstico")

    uploaded_files = st.file_uploader(
        "Sube las transcripciones de las entrevistas (archivos .txt)",
        type=["txt"],
        accept_multiple_files=True
    )

    prompt_diagnostico = st.text_area(
        "Prompt para generar la Matriz de Diagnóstico:",
        height=150,
        value="A partir de las siguientes entrevistas, extrae los principales procesos, actividades y problemas mencionados. Organiza la información en un formato JSON con una lista de objetos, donde cada objeto tenga las claves: 'Proceso', 'Actividad', 'Problema'. Asegúrate de que la respuesta sea únicamente el código JSON válido y nada más."
    )

    if st.button("Generar Matriz de Diagnóstico"):
        if uploaded_files and api_key and prompt_diagnostico:
            with st.spinner("Procesando entrevistas con Gemini Flash..."):
                all_text = ""
                for uploaded_file in uploaded_files:
                    all_text += uploaded_file.read().decode("utf-8") + "\n\n"

                try:
                    # CAMBIO: Lógica para llamar a la API de Gemini
                    model = genai.GenerativeModel('gemini-1.5-flash-latest')
                    # Creamos el contenido completo que enviaremos al modelo
                    full_prompt = f"{prompt_diagnostico}\n\nEntrevistas:\n{all_text}"
                    
                    response = model.generate_content(full_prompt)
                    
                    # Limpiamos la respuesta para asegurar que es solo JSON
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
            st.warning("Asegúrate de subir archivos, tener una clave de API válida y un prompt.")

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
            if api_key and prompt_puo:
                with st.spinner("Generando la matriz PUO con Gemini Flash..."):
                    diagnostico_json = st.session_state['df_diagnostico'].to_json(orient='records')
                    
                    try:
                        # CAMBIO: Lógica para llamar a la API de Gemini
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
                st.warning("Asegúrate de tener una clave de API válida y un prompt.")

# --- Descarga del Archivo Excel ---
if 'df_diagnostico' in st.session_state and 'df_puo' in st.session_state:
    st.header("Paso 3: Descargar Resultados")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state['df_diagnostico'].to_excel(writer, sheet_name='Matriz_Diagnostico', index=False)
        st.session_state['df_puo'].to_excel(writer, sheet_name='Matriz_PUO', index=False)
    
    st.download_button(
        label="📥 Descargar Matrices en Excel",
        data=output.getvalue(),
        file_name="matrices_generadas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
