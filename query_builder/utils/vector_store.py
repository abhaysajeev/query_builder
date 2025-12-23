import os
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import frappe

from query_builder.utils.schema_extractor import build_metadata

# -------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------

COLLECTION_NAME = "query_builder_hrms_schema"

# IMPORTANT: absolute path + forced creation
CHROMA_DIR = os.path.abspath(
    frappe.get_site_path("private/chroma_hrms_schema")
)

# Force directory creation (prevents in-memory fallback)
os.makedirs(CHROMA_DIR, exist_ok=True)

# Load embedding model once
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")


# -------------------------------------------------------------------
# CHROMA CLIENT
# -------------------------------------------------------------------

def get_chroma_client():
    return chromadb.Client(
        Settings(
            persist_directory=CHROMA_DIR,
            is_persistent=True,          # 🔑 THIS IS THE KEY
            anonymized_telemetry=False,
            
        )
    )


# -------------------------------------------------------------------
# SCHEMA → DOCUMENTS
# -------------------------------------------------------------------

def schema_to_documents(schema_list):
    documents = []
    ids = []
    metadatas = []

    for schema in schema_list:
        documents.append(schema["embedding_text"])
        ids.append(f"schema::{schema['doctype']}")
        metadatas.append({
            "doctype": schema["doctype"],
            "module": schema["module"],
            "is_submittable": schema["is_submittable"],
        })

    return documents, ids, metadatas


# -------------------------------------------------------------------
# REBUILD VECTOR STORE
# -------------------------------------------------------------------

def rebuild_vector_store(doctype_list):
    schemas = build_metadata(doctype_list)

    documents, ids, metadatas = schema_to_documents(schemas)

    client = get_chroma_client()

    # clean rebuild
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME)

    embeddings = EMBED_MODEL.encode(documents).tolist()

    collection.add(
        documents=documents,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )

    return {
        "status": "ok",
        "doctypes_indexed": len(documents),
        "chroma_dir": CHROMA_DIR,
    }


# -------------------------------------------------------------------
# RETRIEVE SCHEMA
# -------------------------------------------------------------------

def retrieve_schema(query, top_k=3):
    client = get_chroma_client()
    collection = client.get_collection(COLLECTION_NAME)

    query_embedding = EMBED_MODEL.encode([query]).tolist()[0]

    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )
