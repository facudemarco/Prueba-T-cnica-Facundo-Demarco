import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    
    print("="*60)
    print("CLIENTE INTERACTIVO RAG VIA HTTP (n8n Webhook)")
    print("="*60)
    
    if not webhook_url:
        print("[Error] No se ha configurado la variable N8N_WEBHOOK_URL en el archivo .env")
        print("Por favor, crea un archivo .env basándote en .env.example y configúrala.")
        sys.exit(1)
        
    print(f"Enviando preguntas al webhook de n8n: {webhook_url}")
    print("Escribe tu pregunta y presiona Enter (o escribe 'salir' para terminar).")
    print("-" * 60)
    
    while True:
        try:
            question = input("\nPregunta: ").strip()
            if not question:
                continue
            if question.lower() in ('salir', 'exit', 'quit', 'q'):
                print("¡Hasta luego!")
                break
                
            payload = {"question": question}
            
            # Send HTTP POST to n8n webhook
            response = requests.post(webhook_url, json=payload, timeout=45)
            
            # Check for errors
            response.raise_for_status()
            
            data = response.json()
            
            # Parse the output properties as returned by the n8n workflow
            success = data.get("success", True)
            
            if success:
                answer = data.get("answer", "No se recibió respuesta.")
                sources = data.get("sources", [])
                
                print("\n[Respuesta]:")
                sys.stdout.buffer.write((answer + "\n").encode('utf-8'))
                
                if sources:
                    print(f"\n[Fuentes consultadas]: {', '.join(sources)}")
                else:
                    print("\n[Fuentes consultadas]: Ninguna (respuesta genérica)")
            else:
                error_msg = data.get("error", "Error desconocido en el flujo.")
                print(f"\n[Error de negocio]: {error_msg}")
                
        except requests.exceptions.ConnectionError:
            print("\n[Error de Conexión] No se pudo conectar al webhook de n8n.")
            print("Asegúrate de que n8n esté corriendo y de que el webhook esté activo.")
        except requests.exceptions.Timeout:
            print("\n[Error de Tiempo de Espera] La petición al webhook de n8n excedió el tiempo límite.")
        except requests.exceptions.HTTPError as e:
            print(f"\n[Error HTTP] El servidor retornó un error: {e}")
            try:
                err_data = response.json()
                if "error" in err_data:
                    print(f"Detalle del error: {err_data['error']}")
            except Exception:
                pass
        except KeyboardInterrupt:
            print("\nSaliendo...")
            break
        except Exception as e:
            print(f"\n[Error Inesperado] {e}")

if __name__ == "__main__":
    main()
