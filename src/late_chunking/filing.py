import json
from itertools import groupby
import numpy as np

INDEX_REQUEST_TIMEOUT = 120
FILING_STANDARD_INDEX_NAME = "filing_standard"
FILING_LATE_INDEX_NAME = "filing_late"

def _fmt_vec(vec):
    return "[" + ", ".join(f"{v:7.4f}" for v in vec[:5]) + ", ...]"

def create_index(es):
    filing_mapping_standard = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "section_id": { "type": "keyword" },
                "company_id": { "type": "keyword" },
                "item":       { "type": "keyword" },
                "title":      { "type": "text"    },
                "content":    { "type": "text"    },
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

    filing_mapping_late = {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "section_id": { "type": "keyword" },
                "company_id": { "type": "keyword" },
                "item":       { "type": "keyword" },
                "title":      { "type": "text"    },
                "content":    { "type": "text"    },
                "embedding":  { "type": "dense_vector" },
            }
        }
    }

    print(f"\n=== Filing: Index Creation + Ingestion ===")
    es.options(ignore_status=[404]).indices.delete(index=FILING_STANDARD_INDEX_NAME)
    es.indices.create(index=FILING_STANDARD_INDEX_NAME, body=filing_mapping_standard)
    print(f"  Created  {FILING_STANDARD_INDEX_NAME}")

    es.options(ignore_status=[404]).indices.delete(index=FILING_LATE_INDEX_NAME)
    es.indices.create(index=FILING_LATE_INDEX_NAME, body=filing_mapping_late)
    print(f"  Created  {FILING_LATE_INDEX_NAME}")

def ingest(es, file_path, request_timeout=INDEX_REQUEST_TIMEOUT):
    with open(file_path, "r") as f:
        sections = json.load(f)

    count = 0
    for section in sections:
        document = dict(section)
        document["embedding"] = document['content']

        es.options(request_timeout=request_timeout).index(
            index=FILING_STANDARD_INDEX_NAME,
            id=document["section_id"],
            document=document
        )
        count += 1
    es.indices.refresh(index=FILING_STANDARD_INDEX_NAME)
    print(f"  Indexed  {count} docs → {FILING_STANDARD_INDEX_NAME}")

    # Late embeddings: one API call per company so each filing's context window
    # stays isolated — prevents cross-company entity bleed.
    count = 0
    for _, group in groupby(sections, key=lambda s: s['company_id']):
        company_sections = list(group)
        texts = [s['content'] for s in company_sections]
        response = es.inference.inference(input=texts, inference_id="jina-embeddings-v3-late")
        for section, item in zip(company_sections, response['text_embedding']):
            document = dict(section)
            document["embedding"] = item['embedding']
            es.options(request_timeout=request_timeout).index(
                index=FILING_LATE_INDEX_NAME,
                id=document["section_id"],
                document=document
            )
            count += 1
    es.indices.refresh(index=FILING_LATE_INDEX_NAME)
    print(f"  Indexed  {count} docs → {FILING_LATE_INDEX_NAME}")

    first_id = sections[0]['section_id']
    response = es.get(index=FILING_STANDARD_INDEX_NAME, id=first_id, source_exclude_vectors=False, source_includes=["_inference_fields"])
    std_vec = response['_source']['_inference_fields']['embedding']['inference']['chunks']['embedding'][0]['embeddings']
    response = es.get(index=FILING_LATE_INDEX_NAME, id=first_id, source_exclude_vectors=False, source_includes=["embedding"])
    late_vec = response['_source']['embedding']
    std_arr, late_arr = np.array(std_vec), np.array(late_vec)
    cosine = np.dot(std_arr, late_arr) / (np.linalg.norm(std_arr) * np.linalg.norm(late_arr))

    print(f"\n  Embedding sample  {first_id}")
    print(f"  {'standard':<10}{_fmt_vec(std_vec)}")
    print(f"  {'late':<10}{_fmt_vec(late_vec)}")
    print(f"  {'cosine':<10}{cosine:.4f}")
