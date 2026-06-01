import os
import sys
from vector_store import init_vector_store, SentenceTransformerEF
def retrieve_relevant_chunks(query_text, db_path="./chroma_db", collection_name="docs_collection", n_results=3, similarity_threshold=1.2):
    """Queries the vector database and retrieves matching chunks and their metadata.
    
    Returns:
        dict: A dictionary containing:
            - "is_relevant": bool (True if the closest match's distance is <= threshold)
            - "chunks": list of dicts with keys "id", "content", "metadata", and "distance"
            - "best_distance": float
    """
    client = init_vector_store(db_path)
    
    try:
        emb_fn = SentenceTransformerEF()
        collection = client.get_collection(name=collection_name, embedding_function=emb_fn)
        
        results = collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        
        if not results or not results['ids'] or not results['ids'][0]:
            return {
                "is_relevant": False,
                "chunks": [],
                "best_distance": float('inf')
            }
            
        best_distance = results['distances'][0][0]
        
        if best_distance > similarity_threshold:
            return {
                "is_relevant": False,
                "chunks": [],
                "best_distance": best_distance
            }
            
        chunks = []
        for idx in range(len(results['ids'][0])):
            distance = results['distances'][0][idx]
            
            if distance > similarity_threshold:
                continue
                
            chunks.append({
                "id": results['ids'][0][idx],
                "content": results['documents'][0][idx],
                "metadata": results['metadatas'][0][idx],
                "distance": distance
            })
            
        return {
            "is_relevant": True,
            "chunks": chunks,
            "best_distance": best_distance
        }
        
    except Exception as e:
        print(f"[Error] No se pudo consultar la base de datos vectorial: {e}")
        return {
            "is_relevant": False,
            "chunks": [],
            "best_distance": float('inf')
        }

def query_vector_store(query_text, db_path="./chroma_db", collection_name="docs_collection", n_results=3, similarity_threshold=1.2):
    """Queries the vector database and retrieves matching chunks, formatted as a string."""
    res = retrieve_relevant_chunks(
        query_text=query_text,
        db_path=db_path,
        collection_name=collection_name,
        n_results=n_results,
        similarity_threshold=similarity_threshold
    )
    
    if not res["is_relevant"]:
        return "No tengo información sobre eso."
        
    print(f"\n[Info] Distancia del mejor resultado: {res['best_distance']:.4f} (Umbral: {similarity_threshold})")
    
    output = []
    output.append("=== CONTEXTO ENCONTRADO EN LA DB VECTORIAL ===")
    for idx, chunk in enumerate(res["chunks"]):
        output.append(f"\nResultado #{idx + 1} (Distancia L2: {chunk['distance']:.4f})")
        output.append(f"ID del fragmento: {chunk['id']}")
        output.append(f"Metadatos: {chunk['metadata']}")
        output.append(f"Texto:\n{chunk['content']}")
        output.append("-" * 40)
        
    return "\n".join(output)

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_directory = os.path.join(base_dir, "chroma_db")
    
    print("="*60)
    print("INTERFAZ DE CONSULTA DE LA BASE DE DATOS VECTORIAL")
    print("="*60)
    
    # Check if DB exists
    if not os.path.exists(db_directory):
        print(f"[Error] La base de datos vectorial no se encuentra en {db_directory}.")
        print("Por favor, ejecuta primero: python main.py")
        sys.exit(1)
        
    # Interactive query loop
    print("Escribe tus preguntas para simular el chatbot (o 'salir' para terminar).")
    print("Las preguntas que no correspondan con los documentos recibirán un mensaje genérico.")
    print("-" * 60)
    
    while True:
        try:
            query = input("\nPregunta: ").strip()
            if not query:
                continue
            if query.lower() in ('salir', 'exit', 'quit', 'q'):
                print("Hasta luego!")
                break
                
            response = query_vector_store(
                query_text=query,
                db_path=db_directory,
                collection_name="docs_collection",
                n_results=3,
                similarity_threshold=1.2 # Cosine-distance L2-squared equivalent threshold (adjust as needed)
            )
            
            # Use UTF-8 safe print in Windows console
            sys.stdout.buffer.write((response + "\n").encode('utf-8'))
        except KeyboardInterrupt:
            print("\nSaliendo...")
            break
        except Exception as e:
            print(f"[Error] Ocurrió un error al procesar la consulta: {e}")
