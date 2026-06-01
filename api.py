import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from query import query_vector_store, retrieve_relevant_chunks

# Load environment variables from .env
load_dotenv()

app = FastAPI(
    title="MineCatalog RAG API",
    description="API local para consultar la base de datos vectorial desde n8n",
    version="1.0.0"
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str
    has_info: bool

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    sources: list[str]

@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    """Exposes semantic queries to the ChromaDB vector store.
    
    If no relevant information is found, returns 'No tengo información sobre eso.'
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_directory = os.path.join(base_dir, "chroma_db")
    
    if not os.path.exists(db_directory):
        raise HTTPException(
            status_code=500, 
            detail="La base de datos vectorial no existe. Ejecuta main.py primero."
        )
        
    try:
        # Call query_vector_store with threshold 1.2
        response_text = query_vector_store(
            query_text=request.query,
            db_path=db_directory,
            collection_name="docs_collection",
            n_results=3,
            similarity_threshold=1.2
        )
        
        has_info = response_text != "No tengo información sobre eso."
        
        return QueryResponse(
            response=response_text,
            has_info=has_info
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask", response_model=AskResponse)
def ask_endpoint(request: AskRequest):
    """Answers a question using the retrieved relevant chunks and OpenAI.
    
    If the question is unrelated to the files (distance exceeds threshold),
    returns 'No tengo información sobre eso.'.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_directory = os.path.join(base_dir, "chroma_db")
    
    if not os.path.exists(db_directory):
        raise HTTPException(
            status_code=500, 
            detail="La base de datos vectorial no existe. Ejecuta main.py primero."
        )
        
    try:
        # Retrieve relevant chunks with threshold 1.2
        retrieval_res = retrieve_relevant_chunks(
            query_text=request.question,
            db_path=db_directory,
            collection_name="docs_collection",
            n_results=3,
            similarity_threshold=1.2
        )
        
        # If no relevant chunks are found, return the fallback message
        if not retrieval_res["is_relevant"] or not retrieval_res["chunks"]:
            return AskResponse(
                answer="No tengo información sobre eso.",
                sources=[]
            )
            
        # Extract unique filenames from metadata for sources
        sources = list(set(
            chunk["metadata"].get("filename") 
            for chunk in retrieval_res["chunks"] 
            if chunk["metadata"].get("filename")
        ))
        
        # Concatenate text content of chunks for OpenAI context
        context_text = "\n\n".join([
            f"--- Documento: {chunk['metadata'].get('filename', 'desconocido')} (Fragmento) ---\n{chunk['content']}"
            for chunk in retrieval_res["chunks"]
        ])
        
        # Call OpenAI to formulate the response
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_openai_api_key_here":
            # Fallback if OpenAI key is not provided/configured yet
            # We return the raw best chunk content with a note
            best_chunk = retrieval_res["chunks"][0]["content"]
            return AskResponse(
                answer=f"[Nota: OpenAI API Key no configurada. Mostrando mejor coincidencia directa]\n\n{best_chunk}",
                sources=sources
            )
            
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            
            system_prompt = (
                "Eres un asistente de soporte técnico experto para MineCatalog.\n"
                "Tu tarea es responder la pregunta del usuario utilizando únicamente el contexto proporcionado.\n"
                "Reglas críticas:\n"
                "1. Responde de manera clara y concisa.\n"
                "2. Usa únicamente la información que se detalla en el contexto.\n"
                "3. Si la respuesta no se encuentra en el contexto proporcionado, di exactamente: 'No tengo información sobre eso.'\n"
                "4. No inventes datos ni menciones nada fuera del contexto."
            )
            
            user_prompt = f"Contexto:\n{context_text}\n\nPregunta: {request.question}"
            
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0
            )
            
            answer = completion.choices[0].message.content.strip()
        except Exception as openai_err:
            # Catch billing, quota, network, or key errors and fallback to best chunk
            print(f"[Warning] OpenAI API call failed: {openai_err}. Falling back to best match.")
            best_chunk = retrieval_res["chunks"][0]["content"]
            answer = f"[Nota: Tu cuota/suscripción de OpenAI ha expirado o falló la API. Mostrando coincidencia directa del RAG]\n\n{best_chunk}"
        
        return AskResponse(
            answer=answer,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Force reload to pick up newly installed virtual env dependencies
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
