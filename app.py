import streamlit as st
import pandas as pd
import google.generativeai as genai
import json
from io import BytesIO
from pypdf import PdfReader
import docx

# --- Configuración de la Página ---
st.set_page_config(page_title="Generador de Lista de Actividades", layout="wide")

# --- Título de la Aplicación ---
st.title("Generador Automático de Procesos y Actividades")
st.write("Sube las entrevistas y la IA analizará los textos para crear la lista maestra de actividades de la empresa.")

# --- Manejo Seguro de la Clave API ---
def check_api_key():
    if "GOOGLE_API_KEY" not in st.secrets or not st.secrets["GOOGLE_API_KEY"]:
        st.error("🚨 ¡Error de configuración! La GOOGLE_API_KEY no se ha encontrado en los secrets de Streamlit.")
        st.info("Por favor, ve a la configuración de la app (Settings -> Secrets) y añade tu clave de API de Google.")
        st.stop()
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

check_api_key()

# --- Función para extraer texto ---
def get_text_from_file(uploaded_file):
    text = ""
    try:
        file_name = uploaded_file.name
        if file_name.endswith('.txt'): text = uploaded_file.read().decode("utf-8")
        elif file_name.endswith('.pdf'):
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages: text += page.extract_text() or ""
        elif file_name.endswith('.docx'):
            document = docx.Document(uploaded_file)
            for para in document.paragraphs: text += para.text + "\n"
    except Exception as e:
        st.error(f"Error al leer el archivo {uploaded_file.name}: {e}")
        return None
    return text

# --- Interfaz de la Aplicación ---
with st.container(border=True):
    st.header("Paso 1: Cargar las Entrevistas")
    
    files_entrevistas = st.file_uploader(
        "Sube uno o más archivos de entrevistas (.txt, .pdf, .docx)",
        type=["txt", "pdf", "docx"],
        accept_multiple_files=True
    )

with st.container(border=True):
    st.header("Paso 2: Generar la Lista de Actividades")
    
    # TU PROMPT ADAPTADO
    prompt_base = st.text_area(
        "Prompt para generar la lista de actividades:",
        height=300,
        value="""Analiza todas las transcripciones de entrevistas proporcionadas.
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
    )

    if st.button("Generar Lista de Actividades", type="primary"):
        if files_entrevistas:
            with st.spinner("Analizando entrevistas y generando la lista..."):
                texto_entrevistas = ""
                for file in files_entrevistas:
                    texto_entrevistas += get_text_from_file(file) + "\n\n---\n\n"

                full_prompt = f"{prompt_base}\n\n--- INICIO ENTREVISTAS ---\n{texto_entrevistas}\n--- FIN ENTREVISTAS ---"
                
                try:
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content(full_prompt)
                    
                    cleaned_response = response.text.strip().replace("```json", "").replace("```", "")
                    json_data = json.loads(cleaned_response)
                    
                    df_resultado = pd.DataFrame(json_data)
                    
                    st.session_state['df_resultado'] = df_resultado
                    st.success("¡Lista de actividades generada con éxito!")
                    st.dataframe(df_resultado)

                except Exception as e:
                    st.error(f"Ocurrió un error al generar la lista: {e}")
                    st.error(f"Respuesta recibida del modelo: {response.text if 'response' in locals() else 'No response'}")
        else:
            st.warning("Por favor, sube al menos un archivo de entrevista.")

# --- Descarga del Archivo Excel ---
if 'df_resultado' in st.session_state:
    st.header("Paso 3: Descargar el Archivo")
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state['df_resultado'].to_excel(writer, sheet_name='Lista_Actividades', index=False)
    
    st.download_button(
        label="📥 Descargar Lista en Excel",
        data=output.getvalue(),
        file_name="lista_de_actividades.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
