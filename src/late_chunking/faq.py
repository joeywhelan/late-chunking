import json
import numpy as np

INDEX_REQUEST_TIMEOUT = 120
FAQ_STANDARD_INDEX_NAME = "faq_standard"
FAQ_LATE_INDEX_NAME = "faq_late"

def _fmt_vec(vec):
    return "[" + ", ".join(f"{v:7.4f}" for v in vec[:5]) + ", ...]"

def create_index(es):
    faq_mapping_standard = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "entry_id":  { "type": "keyword" },
                "category":  { "type": "keyword" },
                "question":  { "type": "text"    },
                "answer":    { "type": "text"    },
                "embedding": { 
                    "type": "semantic_text", 
                    "inference_id": "jina-embeddings-v3-standard",
                    "chunking_settings": {
                        "strategy": "none"
                    } 
                },
            }
        }
    }

    faq_mapping_late = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "entry_id":  { "type": "keyword" },
                "category":  { "type": "keyword" },
                "question":  { "type": "text" },
                "answer":    { "type": "text" },
                "embedding": { "type": "dense_vector" } ,
            }
        }
    }

    print(f"\n=== FAQ: Index Creation + Ingestion ===")
    es.options(ignore_status=[404]).indices.delete(index=FAQ_STANDARD_INDEX_NAME)
    es.indices.create(index=FAQ_STANDARD_INDEX_NAME, body=faq_mapping_standard)
    print(f"  Created  {FAQ_STANDARD_INDEX_NAME}")

    es.options(ignore_status=[404]).indices.delete(index=FAQ_LATE_INDEX_NAME)
    es.indices.create(index=FAQ_LATE_INDEX_NAME, body=faq_mapping_late)
    print(f"  Created  {FAQ_LATE_INDEX_NAME}")

def ingest(es, file_path, request_timeout=INDEX_REQUEST_TIMEOUT):
    with open(file_path, "r") as f:
        faqs = json.load(f)

    count = 0
    qa_texts = []
    for faq in faqs:
        document = dict(faq)
        text = document['answer']
        document["embedding"] = text

        es.options(request_timeout=request_timeout).index(
            index=FAQ_STANDARD_INDEX_NAME,
            id=document["entry_id"],
            document=document
        )
        qa_texts.append(text)
        count += 1
    es.indices.refresh(index=FAQ_STANDARD_INDEX_NAME)
    print(f"  Indexed  {count} docs → {FAQ_STANDARD_INDEX_NAME}")
    
    response = es.inference.inference(input=qa_texts, inference_id="jina-embeddings-v3-late")
    embeddings = [item['embedding'] for item in response['text_embedding']]

    count = 0
    for faq in faqs:
        document = dict(faq)
        document["embedding"] = embeddings[count]
        es.options(request_timeout=request_timeout).index(
            index=FAQ_LATE_INDEX_NAME,
            id=document["entry_id"],
            document=document
        )
        count += 1
    es.indices.refresh(index=FAQ_LATE_INDEX_NAME)
    print(f"  Indexed  {count} docs → {FAQ_LATE_INDEX_NAME}")

    response = es.get(index=FAQ_STANDARD_INDEX_NAME, id="FAQ-001", source_exclude_vectors=False, source_includes=["_inference_fields"])
    std_vec = response['_source']['_inference_fields']['embedding']['inference']['chunks']['embedding'][0]['embeddings']
    response = es.get(index=FAQ_LATE_INDEX_NAME, id="FAQ-001", source_exclude_vectors=False, source_includes=["embedding"])
    late_vec = response['_source']['embedding']
    std_arr, late_arr = np.array(std_vec), np.array(late_vec)
    cosine = np.dot(std_arr, late_arr) / (np.linalg.norm(std_arr) * np.linalg.norm(late_arr))

    print(f"\n  Embedding sample  FAQ-001")
    print(f"  {'standard':<10}{_fmt_vec(std_vec)}")
    print(f"  {'late':<10}{_fmt_vec(late_vec)}")
    print(f"  {'cosine':<10}{cosine:.4f}")
    