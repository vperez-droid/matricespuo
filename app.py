# app.py

import streamlit as st
import pandas as pd
from openai import OpenAI
import json
from io import BytesIO

# --- Configuración de la Página ---
st.set_page_config(page_title="Generador de Matrices PUO", layout="wide")

# --- Título de la Aplicación ---
st.title("Generador Automático de Matrices de Diagnóstico y PUO")
st.write("Sube transcripciones de entrevistas para generar una matriz de diagnóstico y luego una matriz PUO.")

# --- Manejo Seguro de la Clave API ---
# Intenta obtener la clave desde los secrets de Streamlit (para despliegue)
try:
    api_key = st.secrets["OPENAI_API_KEY"]
except KeyError:
    st.warning("Clave de API no encontrada en los secrets. Por favor, ingrésala manualmente para uso local.")
    api_key = st.text_input("Ingresa tu clave de API de OpenAI", type="password")

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
        value="A partir de las siguientes entrevistas, extrae los principales procesos, actividades y problemas mencionados. Organiza la información en un formato JSON con una lista de objetos, donde cada objeto tenga las claves: 'Proceso', 'Actividad', 'Problema'."
    )

    if st.button("Generar Matriz de Diagnóstico"):
        if uploaded_files and api_key and prompt_diagnostico:
            with st.spinner("Procesando entrevistas y generando la matriz de diagnóstico..."):
                all_text = ""
                for uploaded_file in uploaded_files:
                    all_text += uploaded_file.read().decode("utf-8") + "\n\n"

                client = OpenAI(api_key=api_key)
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Eres un asistente que extrae información de textos y la estructura en formato JSON."},
                            {"role": "user", "content": f"{prompt_diagnostico}\n\nEntrevistas:\n{all_text}"}
                        ]
                    )
                    
                    json_response = json.loads(response.choices[0].message.content)
                    df_diagnostico = pd.DataFrame(json_response)
                    
                    st.session_state['df_diagnostico'] = df_diagnostico
                    st.success("Matriz de Diagnóstico generada con éxito.")
                    st.dataframe(df_diagnostico)

                except Exception as e:
                    st.error(f"Ocurrió un error al generar la matriz de diagnóstico: {e}")
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
            value="A partir de la siguiente matriz de diagnóstico en formato JSON, crea una matriz PUO. Identifica el problema principal, el usuario afectado y define un objetivo claro de mejora. Devuelve el resultado en un formato JSON con una lista de objetos, donde cada objeto tenga las claves: 'Problema', 'Usuario Afectado', 'Objetivo de Mejora'."
        )

        if st.button("Generar Matriz PUO"):
            if api_key and prompt_puo:
                with st.spinner("Generando la matriz PUO..."):
                    diagnostico_json = st.session_state['df_diagnostico'].to_json(orient='records')
                    
                    client = OpenAI(api_key=api_key)
                    try:
                        response = client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "Eres un asistente que transforma datos de diagnóstico en una matriz PUO en formato JSON."},
                                {"role": "user", "content": f"{prompt_puo}\n\nMatriz de Diagnóstico:\n{diagnostico_json}"}
                            ]
                        )
                        
                        json_response_puo = json.loads(response.choices[0].message.content)
                        df_puo = pd.DataFrame(json_response_puo)
                        
                        st.session_state['df_puo'] = df_puo
                        st.success("Matriz PUO generada con éxito.")
                        st.dataframe(df_puo)

                    except Exception as e:
                        st.error(f"Ocurrió un error al generar la matriz PUO: {e}")
            else:
                st.warning("Asegúrate de tener una clave de API válida y un prompt.")

# --- Descarga del Archivo Excel ---
if 'df_diagnostico' in st.session_state and 'df_puo' in st.session_state:
    st.header("Paso 3: Descargar Resultados")
    
    output = BytesIO()
    # Usar 'xlsxwriter' como motor para crear el archivo Excel en memoria
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state['df_diagnostico'].to_excel(writer, sheet_name='Matriz_Diagnostico', index=False)
        st.session_state['df_puo'].to_excel(writer, sheet_name='Matriz_PUO', index=False)
    
    st.download_button(
        label="📥 Descargar Matrices en Excel",
        data=output.getvalue(),
        file_name="matrices_generadas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
