import os
from reader import read_all_documents
from cleaner import clean_and_chunk_documents
from vector_store import init_vector_store, save_chunks_to_vector_store

def run_pipeline(docs_dir="./docs", db_path="./chroma_db", collection_name="docs_collection"):
    """Orchestrates the reading, cleaning, chunking, and vector indexing pipeline."""
    print("="*60)
    print("INICIANDO PIPELINE DE LIMPIEZA Y VECTORIZACIÓN DE DOCUMENTOS")
    print("="*60)
    
    # 1. Leer los archivos de la carpeta /docs
    print("\n--- PASO 1: LECTURA DE ARCHIVOS ---")
    documents = read_all_documents(docs_dir)
    print(f"Total de documentos/páginas cargados del disco: {len(documents)}")
    
    if not documents:
        print("[Warning] No se encontraron documentos válidos en la carpeta '/docs'. Abortando.")
        return
        
    # 2. Limpiar y fragmentar (chunking) los datos
    print("\n--- PASO 2: LIMPIEZA Y FRAGMENTACIÓN (CHUNKING) ---")
    chunks = clean_and_chunk_documents(
        documents=documents,
        max_chunk_size=1000,
        overlap=150
    )
    print(f"Total de fragmentos (chunks) generados después de la limpieza: {len(chunks)}")
    
    # 3. Guardar en base de datos vectorial
    print("\n--- PASO 3: INDEXACIÓN EN BASE DE DATOS VECTORIAL (CHROMADB) ---")
    db_client = init_vector_store(db_path=db_path)
    
    save_chunks_to_vector_store(
        client=db_client,
        chunks=chunks,
        collection_name=collection_name,
        clear_existing=True,
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    
    print("\n" + "="*60)
    print("PIPELINE COMPLETADO CON ÉXITO")
    print("="*60)
    
    # Print metrics
    files_processed = len(set(doc["metadata"]["filename"] for doc in documents))
    print(f"Estadísticas finales:")
    print(f" - Archivos leídos con éxito: {files_processed}")
    print(f" - Documentos lógicos de origen: {len(documents)}")
    print(f" - Fragmentos indexados en la DB vectorial: {len(chunks)}")
    print(f" - Ubicación de base de datos: {os.path.abspath(db_path)}")
    print("="*60)

if __name__ == "__main__":
    # Base directory configurations
    base_dir = os.path.dirname(os.path.abspath(__file__))
    docs_directory = os.path.join(base_dir, "docs")
    db_directory = os.path.join(base_dir, "chroma_db")
    
    run_pipeline(
        docs_dir=docs_directory,
        db_path=db_directory,
        collection_name="docs_collection"
    )
