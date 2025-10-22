# README.md

# Generador Automático de Matrices de Diagnóstico y PUO

Esta es una aplicación web creada con Streamlit que automatiza la creación de matrices de diagnóstico y PUO (Problema, Usuario, Objetivo) a partir de transcripciones de entrevistas.

## 🚀 ¿Cómo funciona?

1.  **Carga de Entrevistas**: Sube uno o más archivos de texto (`.txt`) con las transcripciones de las entrevistas.
2.  **Generar Matriz de Diagnóstico**: Usando un prompt personalizable, la aplicación procesa el texto con la API de OpenAI para identificar procesos, actividades y problemas, mostrando el resultado en una tabla.
3.  **Generar Matriz PUO**: A partir de la matriz de diagnóstico generada, un segundo prompt crea una matriz PUO, identificando el problema, el usuario afectado y un objetivo de mejora.
4.  **Descargar en Excel**: Ambas matrices pueden ser descargadas en un único archivo de Excel, cada una en una hoja separada.

## 🛠️ Despliegue

Esta aplicación está diseñada para ser desplegada en [Streamlit Community Cloud](https://streamlit.io/cloud).

### Configuración de la Clave de API

Para que la aplicación funcione, es necesario añadir tu clave de API de OpenAI en los "Secrets" de Streamlit Community Cloud con el siguiente formato:

```toml
# .streamlit/secrets.toml
OPENAI_API_KEY = "tu-clave-secreta-aqui"
```

## 💻 Ejecución Local

Para ejecutar esta aplicación en tu máquina local:

1.  **Clona el repositorio:**
    ```bash
    git clone [URL-DE-TU-REPOSITORIO]
    cd [NOMBRE-DEL-REPOSITORIO]
    ```

2.  **Crea un entorno virtual e instala las dependencias:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Ejecuta la aplicación:**
    ```bash
    streamlit run app.py
    ```
