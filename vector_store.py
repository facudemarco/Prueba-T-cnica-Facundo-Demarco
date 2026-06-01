import os
import chromadb
from chromadb import EmbeddingFunction, Documents, Embeddings

class SentenceTransformerEF(EmbeddingFunction):
    """Custom embedding function wrapping SentenceTransformers for ChromaDB."""
    def __init__(self, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Cargando modelo de embeddings: {model_name}...")
            self.model = SentenceTransformer(model_name)
            print("Modelo cargado exitosamente.")
        except Exception as e:
            print(f"[Error] No se pudo cargar el modelo '{model_name}': {e}")
            raise e

    def __call__(self, input: Documents) -> Embeddings:
        # Generate embeddings using SentenceTransformers
        embeddings = self.model.encode(input, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

def init_vector_store(db_path="./chroma_db"):
    """Initializes and returns a persistent ChromaDB client."""
    os.makedirs(db_path, exist_ok=True)
    print(f"Inicializando ChromaDB persistente en: {os.path.abspath(db_path)}")
    return chromadb.PersistentClient(path=db_path)

def save_chunks_to_vector_store(client, chunks, collection_name="docs_collection", clear_existing=True, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    """Saves a list of chunks to a ChromaDB collection.
    
    Each chunk is a dict: {"content": str, "metadata": dict}
    
    If clear_existing is True, any existing collection with collection_name is deleted first.
    """
    if not chunks:
        print("[Warning] No hay fragmentos (chunks) para guardar en la base de datos vectorial.")
        return
        
    try:
        # Load embedding function
        emb_fn = SentenceTransformerEF(model_name=model_name)
    except Exception as e:
        print(f"[Error] Falló la inicialización de los embeddings. Abortando guardado en la DB: {e}")
        return
        
    try:
        # Clear existing collection if requested
        if clear_existing:
            try:
                client.delete_collection(name=collection_name)
                print(f"Colección existente '{collection_name}' eliminada para una carga limpia.")
            except Exception:
                # Collection does not exist or deletion failed, ignore
                pass
                
        # Create or get collection
        collection = client.create_collection(
            name=collection_name,
            embedding_function=emb_fn,
            metadata={"description": "Documentos técnicos limpios para chatbot RAG"}
        )
        
        # Prepare lists for insertion
        ids = []
        documents_text = []
        metadatas = []
        
        for idx, chunk in enumerate(chunks):
            content = chunk["content"]
            meta = chunk["metadata"]
            
            # Generate a unique and descriptive ID for the chunk
            filename = meta.get("filename", "unknown").replace(" ", "_")
            page_info = f"_page_{meta['page']}" if "page" in meta else ""
            item_info = f"_item_{meta['item_index']}" if "item_index" in meta else ""
            chunk_idx = meta.get("chunk_index", idx)
            
            chunk_id = f"{filename}{page_info}{item_info}_chunk_{chunk_idx}"
            
            ids.append(chunk_id)
            documents_text.append(content)
            
            # Ensure metadata keys and values are simple types (str, int, float, bool)
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            metadatas.append(clean_meta)
            
        print(f"Insertando {len(documents_text)} fragmentos en la colección '{collection_name}'...")
        
        # Insert in batches of 100 to avoid limits or large payloads issues
        batch_size = 100
        for i in range(0, len(documents_text), batch_size):
            end_idx = min(i + batch_size, len(documents_text))
            collection.add(
                ids=ids[i:end_idx],
                documents=documents_text[i:end_idx],
                metadatas=metadatas[i:end_idx]
            )
            print(f"Indexados fragmentos {i+1} a {end_idx} de {len(documents_text)}...")
            
        print(f"Éxito: Se guardaron {len(documents_text)} fragmentos en la base de datos vectorial.")
        
    except Exception as e:
        print(f"[Error] Ocurrió un error al guardar los fragmentos en la base de datos vectorial: {e}")
