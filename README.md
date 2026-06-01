# Prueba Técnica – Facundo Demarco

Este repositorio contiene la resolución de la Prueba Técnica para el puesto de **Machine Learning Engineer Jr**

La solución implementa una arquitectura RAG (Retrieval-Augmented Generation) de extremo a extremo que procesa documentación técnica, la indexa en una base de datos vectorial local, expone endpoints HTTP para su consumo y se integra con un orquestador n8n.

---

## 🏗️ Arquitectura de la Solución

El flujo de ejecución consta de los siguientes componentes:

1. **Pipeline de Ingesta (Python)**: Lee documentos de diversos formatos (`.txt`, `.md`, `.json`, `.pdf`), limpia y elimina ruido, divide el texto en fragmentos (chunking) y genera embeddings para indexarlos en una base de datos vectorial local (**ChromaDB**).
2. **Orquestador (n8n)**: Recibe consultas HTTP mediante un webhook público, valida el contenido y reenvía la pregunta a la API local de Python a través de un túnel seguro.
3. **API Local de RAG (FastAPI)**:
   - Busca en ChromaDB los fragmentos semánticamente más similares.
   - Evalúa un umbral de distancia. Si la consulta es ajena a la documentación, responde inmediatamente con un mensaje genérico para evitar alucinaciones y consumo innecesario de tokens.
   - Si la consulta es relevante, construye el contexto y realiza una petición a OpenAI (`gpt-4o-mini`) para generar la respuesta final.
   - Implementa un **fallback robusto**: Si la API Key de OpenAI expira, se queda sin cuota (error 429) o falla, el sistema captura el error y devuelve de forma limpia la mejor coincidencia directa de la base de datos con una nota aclaratoria, evitando caídas del servicio (error 500).
4. **Cliente de Consola interactivo**: Envía preguntas por HTTP al webhook de n8n para simular de forma sencilla la interacción de un usuario.

---

## 📁 Estructura del Proyecto

- [docs/](./docs): Carpeta que contiene la documentación técnica de soporte proporcionada (archivos `.txt`, `.md`, `.json`, `.pdf`).
- [workflows/](./workflows): Contiene el flujo de trabajo exportado listo para importar en n8n:
  - [Workflow Prueba Tecnica - Facundo Demarco.json](./workflows/Workflow%20Prueba%20Tecnica%20-%20Facundo%20Demarco.json).
- [api.py](./api.py): Servidor FastAPI que expone los endpoints `/ask` y `/query`.
- [main.py](./main.py): Script principal que orquesta el pipeline de lectura, limpieza e indexación.
- [cleaner.py](./cleaner.py): Módulo con lógica de limpieza de texto, remoción de caracteres basura y chunking con solapamiento (overlap).
- [reader.py](./reader.py): Lógica de lectura multi-formato de archivos en la carpeta de origen.
- [vector_store.py](./vector_store.py): Módulo de interacción con ChromaDB y generación de embeddings locales (`sentence-transformers`).
- [query.py](./query.py): Lógica de consulta directa y evaluación de distancia semántica.
- [query_http.py](./query_http.py): Cliente CLI interactivo que envía peticiones al webhook de n8n.
- [requirements.txt](./requirements.txt): Archivo de dependencias del proyecto.
- [.env.example](./.env.example): Plantilla de configuración de variables de entorno.

---

## 🛠️ Requisitos Previos

Asegúrate de tener instalados los siguientes componentes:

- **Python 3.10** o superior.
- Una cuenta en **n8n** (ya sea local o n8n Cloud).
- **ngrok** (o localtunnel) instalado para exponer tu puerto local al servidor de n8n.

---

## 🚀 Guía de Instalación y Configuración

### 1. Clonar el repositorio e instalar dependencias

Abre una terminal en la raíz del proyecto y ejecuta:

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# En Windows (Powershell):
.\venv\Scripts\Activate.ps1
# En macOS/Linux:
source venv/bin/activate

# Actualizar pip e instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto basándote en la plantilla `.env.example`:

```bash
cp .env.example .env
```

Edita el archivo `.env` configurando tus credenciales y URLs correspondientes:

```env
# Tu clave de API de OpenAI para generar las respuestas del RAG
OPENAI_API_KEY

# La URL pública de pruebas del Webhook de n8n
N8N_WEBHOOK_URL
```

### 3. Ejecutar el Pipeline de Ingesta (Lectura y Vectorización)

Ejecuta el script para procesar los documentos técnicos y subirlos a la base de datos vectorial local:

```bash
python main.py
```

_Este proceso leerá todos los archivos en `/docs`, aplicará técnicas de limpieza, generará los fragmentos de texto y creará la base de datos persistente en la carpeta `./chroma_db`._

### 4. Iniciar el Servidor API de Python

Levanta el servidor web FastAPI local:

```bash
uvicorn api:app --reload
```

_El servidor estará disponible de forma local en `http://127.0.0.1:8000`._

### 5. Exponer el puerto local a internet (ngrok)

Dado que n8n se ejecuta en la nube, necesitas exponer tu puerto local `8000`. Abre otra terminal y ejecuta:

```bash
ngrok http 8000
```

Copia la URL pública `https://...ngrok-free.app` generada por ngrok.

### 6. Configurar el Workflow en n8n

1. Ingresa a tu panel de n8n e importa el archivo [Workflow Prueba Tecnica - Facundo Demarco.json](./workflows/Workflow%20Prueba%20Tecnica%20-%20Facundo%20Demarco.json).
2. Abre el nodo **"Consultar API Python local"** (HTTP Request) y realiza los siguientes cambios:
   - **URL**: Reemplaza `http://localhost:8000/ask` con la URL de tu túnel de ngrok (ejemplo: `https://tu-id-ngrok.ngrok-free.app/ask`).
   - **Headers**: Conserva el encabezado `ngrok-skip-browser-warning: true` (incluido en el JSON) para evitar que la pantalla de protección de ngrok bloquee las llamadas automáticas del flujo.
3. Guarda el flujo de trabajo en n8n y ponlo en modo escucha activa (haz clic en **Listen for test event**).

---

## 🧪 Pruebas de Funcionamiento

Una vez que tengas la API corriendo, el túnel ngrok configurado y n8n en modo prueba, puedes iniciar la simulación interactiva:

```bash
python query_http.py
```

### Casos de prueba evaluados:

1. **Pregunta válida contenida en la documentación**:
   - _Consulta_: `¿Cómo reinicio el servicio de autenticación?`
   - _Respuesta_: Respuestas claras basadas en el contexto del documento y la lista de fuentes consultadas (ej. `[Fuentes consultadas]: Documentación 1.pdf`).
2. **Pregunta fuera del contexto de la documentación**:
   - _Consulta_: `¿Cómo preparo una tarta de chocolate?`
   - _Respuesta_: `No tengo información sobre eso.` _(El sistema bloquea la consulta a nivel de base de datos vectorial debido a la distancia de similitud superior a 1.2, ahorrando tokens de OpenAI)_.
3. **Manejo de entradas vacías**:
   - Si presionas enter sin escribir nada, el validador del webhook en n8n intercepta la petición y responde con un código `400 Bad Request` indicando que la pregunta no puede estar vacía.
4. **Manejo de errores de API (ej. Sin Saldo/Quota en OpenAI)**:
   - Si la API Key de OpenAI no está configurada o se ha quedado sin saldo (`insufficient_quota`), el backend FastAPI de Python capturará el error de forma transparente y te responderá con la coincidencia directa más cercana del RAG local para que no falle el flujo.
