# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Launch notebook
uv run jupyter notebook demo.ipynb

# Terraform (from terraform/)
terraform init
terraform apply
terraform destroy
```

Environment variables are loaded from `.env` — copy `terraform/terraform.tfvars.sample` as a reference for what credentials are needed (Elastic Cloud API key, Jina API key).

## Architecture

This is a research project that empirically demonstrates when late chunking helps vs. hurts retrieval quality. The main deliverable is `demo.ipynb`.

### Thesis

Late chunking is not a universal upgrade — it's a specialized tool. The experiment proves both sides: measurable degradation on self-contained content (Corpus A) and measurable improvement on cross-referenced content (Corpus B).

### Two Corpora

| File | Content | Expected outcome |
|------|---------|-----------------|
| `assets/corpus_a_product_catalog.json` | 50 self-contained product descriptions (MegaMart catalog). No cross-references; adjacent items are semantically unrelated. | Late chunking **hurts**: context bleeds between unrelated products. |
| `assets/corpus_b_maintenance_manual.json` | 20 sections of MA-9200 aircraft landing gear manual. Dense cross-references: tool IDs (T-14, T-22…), material codes (C-101–C-105), section refs, pronouns. | Late chunking **helps**: isolated chunks lose the cross-reference context; full-document embedding captures it. |

### Embedding Strategy

- **Standard path**: each chunk (product or manual section) embedded independently via Jina v3 API
- **Late chunking path**: full document passed to Jina v3 with late chunking enabled → per-chunk embeddings returned

This produces four Elasticsearch indices: `corpus-a-standard`, `corpus-a-late`, `corpus-b-standard`, `corpus-b-late`.

### Measurement

Queries run against both index variants per corpus. Metrics: cosine similarity of top result, Mean Reciprocal Rank (MRR), hit rate (correct chunk in top-k).

### Infrastructure

Terraform in `terraform/` provisions an Elastic Cloud Serverless Elasticsearch project (`gcp-us-central1` by default). Outputs: Elasticsearch URL, Kibana URL, Cloud ID, scoped API key for notebook use.

### Notebook Structure

1. Setup & configuration — credentials, Jina helper functions
2. Index creation — four indices with identical mappings
3. Chunking & embedding — standard and late paths
4. Query set — 10–20 queries per corpus with ground truth chunk IDs
5. Retrieval & measurement — MRR, hit rate, cosine similarity
6. Results & visualization — side-by-side tables/charts
7. Cleanup — delete indices

### Open Blocker

Jina v3 late chunking API details are unconfirmed (exact parameter name, max input length, whether chunk boundaries are caller-specified or model-determined). All embedding helper code depends on this.

See `assets/plan.md` for the full task breakdown and open questions.
