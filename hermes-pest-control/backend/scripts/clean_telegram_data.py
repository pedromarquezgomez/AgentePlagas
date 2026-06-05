#!/usr/bin/env python3
import asyncio
import os
import sys
from pathlib import Path

# Asegurar que el path del backend esté disponible por si acaso
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from google.cloud import firestore
except ImportError:
    print("Error: El paquete 'google-cloud-firestore' no está instalado en este entorno.")
    print("Por favor, asegúrate de activar el entorno virtual y tener las dependencias instaladas.")
    sys.exit(1)

async def clean_telegram_data(target_telegram_id: str | None = None, force: bool = False) -> None:
    project_id = os.environ.get("FIREBASE_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT") or "control-plagas-ai"
    print(f"Conectando a Firestore en el proyecto: {project_id}...")
    
    try:
        db = firestore.AsyncClient(project=project_id)
    except Exception as e:
        print(f"Error al inicializar el cliente de Firestore: {e}")
        return

    # Determinar prefijo o ID exacto de conversación
    if target_telegram_id:
        # Limpiar un usuario de Telegram específico
        target_conv_id = f"telegram:{target_telegram_id}"
        print(f"\nModo: Limpiar datos únicamente para el usuario de Telegram '{target_telegram_id}' ({target_conv_id})")
    else:
        # Limpiar todas las conversaciones de Telegram
        target_conv_id = None
        print("\nModo: Limpiar TODAS las conversaciones e incidencias relacionadas con Telegram.")

    # Colecciones a limpiar
    collections_to_clean = ["conversations", "messages", "incidents", "tool_execution_records", "customers"]
    deleted_counts = {col: 0 for col in collections_to_clean}

    if not force:
        confirm = input("\n¿Estás seguro de que deseas proceder con el borrado? (Escribe 'si' para confirmar): ")
        if confirm.strip().lower() not in ["si", "sí"]:
            print("Operación cancelada.")
            return

    print("\nIniciando borrado...")

    # 1. Borrar de 'conversations'
    print("Procesando colección 'conversations'...")
    try:
        conv_ref = db.collection("conversations")
        if target_conv_id:
            doc = conv_ref.document(target_conv_id)
            if (await doc.get()).exists:
                await doc.delete()
                deleted_counts["conversations"] += 1
                print(f"  - Conversación '{target_conv_id}' eliminada.")
        else:
            # Borrar todos los documentos cuyo ID empiece con 'telegram:'
            async for doc in conv_ref.list_documents():
                if doc.id.startswith("telegram:"):
                    await doc.delete()
                    deleted_counts["conversations"] += 1
                    print(f"  - Conversación '{doc.id}' eliminada.")
    except Exception as e:
        print(f"  Error en 'conversations': {e}")

    # 2. Borrar de 'messages'
    print("Procesando colección 'messages'...")
    try:
        msg_ref = db.collection("messages")
        # En Firestore no podemos hacer queries complejas en list_documents,
        # así que usamos queries filtrando por 'conversation_id'.
        if target_conv_id:
            query = msg_ref.where("conversation_id", "==", target_conv_id)
            async for doc in query.stream():
                await msg_ref.document(doc.id).delete()
                deleted_counts["messages"] += 1
        else:
            # Para borrar todos los mensajes de Telegram, iteramos y buscamos los que tengan prefix telegram:
            # Dado que puede haber muchos mensajes, lo hacemos por streams
            async for doc in msg_ref.stream():
                conv_id = doc.get("conversation_id")
                if conv_id and str(conv_id).startswith("telegram:"):
                    await msg_ref.document(doc.id).delete()
                    deleted_counts["messages"] += 1
    except Exception as e:
        print(f"  Error en 'messages': {e}")

    # 3. Borrar de 'incidents'
    print("Procesando colección 'incidents'...")
    try:
        inc_ref = db.collection("incidents")
        if target_conv_id:
            query = inc_ref.where("conversation_id", "==", target_conv_id)
            async for doc in query.stream():
                await inc_ref.document(doc.id).delete()
                deleted_counts["incidents"] += 1
        else:
            async for doc in inc_ref.stream():
                conv_id = doc.get("conversation_id")
                if conv_id and str(conv_id).startswith("telegram:"):
                    await inc_ref.document(doc.id).delete()
                    deleted_counts["incidents"] += 1
    except Exception as e:
        print(f"  Error en 'incidents': {e}")

    # 4. Borrar de 'tool_execution_records'
    print("Procesando colección 'tool_execution_records'...")
    try:
        tool_ref = db.collection("tool_execution_records")
        if target_conv_id:
            # Borrar por metadata.conversation_id o conversation_id
            query1 = tool_ref.where("conversation_id", "==", target_conv_id)
            async for doc in query1.stream():
                await tool_ref.document(doc.id).delete()
                deleted_counts["tool_execution_records"] += 1
            
            # Buscar también en metadata
            async for doc in tool_ref.stream():
                metadata = doc.get("metadata") or {}
                if metadata.get("conversation_id") == target_conv_id:
                    # Evitar doble borrado si ya se borró
                    doc_ref = tool_ref.document(doc.id)
                    if (await doc_ref.get()).exists:
                        await doc_ref.delete()
                        deleted_counts["tool_execution_records"] += 1
        else:
            async for doc in tool_ref.stream():
                conv_id = doc.get("conversation_id")
                metadata = doc.get("metadata") or {}
                meta_conv_id = metadata.get("conversation_id")
                if (conv_id and str(conv_id).startswith("telegram:")) or (meta_conv_id and str(meta_conv_id).startswith("telegram:")):
                    await tool_ref.document(doc.id).delete()
                    deleted_counts["tool_execution_records"] += 1
    except Exception as e:
        print(f"  Error en 'tool_execution_records': {e}")

    # 5. Desvincular de 'customers' (para olvidar la asociación de nombre con Telegram)
    print("Procesando colección 'customers' (desvinculando telegram_user_id)...")
    try:
        cust_ref = db.collection("customers")
        if target_telegram_id:
            query = cust_ref.where("telegram_user_id", "==", target_telegram_id)
            async for doc in query.stream():
                await cust_ref.document(doc.id).update({"telegram_user_id": None})
                deleted_counts["customers"] += 1
                print(f"  - Desvinculado telegram_user_id del cliente '{doc.id}' ({doc.get('name')}).")
        else:
            async for doc in cust_ref.stream():
                tg_uid = doc.get("telegram_user_id")
                if tg_uid:
                    await cust_ref.document(doc.id).update({"telegram_user_id": None})
                    deleted_counts["customers"] += 1
                    print(f"  - Desvinculado telegram_user_id del cliente '{doc.id}' ({doc.get('name')}).")
    except Exception as e:
        print(f"  Error en 'customers': {e}")

    print("\n==================================================")
    print(" RESUMEN DE LIMPIEZA DE TELEGRAM")
    print("==================================================")
    for col, count in deleted_counts.items():
        print(f"  - Documentos eliminados en '{col}': {count}")
    print("==================================================")
    print("✔ BBDD de Telegram limpiada con éxito. ¡Ya puedes empezar de cero!")

if __name__ == "__main__":
    telegram_id = None
    force = False
    
    for arg in sys.argv[1:]:
        if arg in ["--yes", "-y"]:
            force = True
        else:
            telegram_id = arg.strip()
            
    asyncio.run(clean_telegram_data(telegram_id, force))
