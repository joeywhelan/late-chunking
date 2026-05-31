# Plan: Late Chunking — When It Helps, When It Hurts

## Thesis

Most writing about late chunking shows it succeeding. This article and demo take the
opposite angle: **late chunking is a tool with a specific job, not a universal upgrade**.
We demonstrate both sides with real retrieval numbers — the measurable degradation when
late chunking is applied to self-contained content, and the measurable improvement when
it is applied to cross-referential content where document-level context is essential.

The goal is to give engineers an empirical basis for choosing a chunking strategy, not
just a recommendation to trust.

---

## Tech Stack

| Component        | Choice                                              |
|------------------|-----------------------------------------------------|
| Embedding model  | `jina-embeddings-v3` via Jina API                   |
| Vector store     | Elastic Cloud Serverless (Elasticsearch project)    |
| Infrastructure   | Terraform (provision Elastic Serverless)            |
| Demo             | Python notebook (Jupyter)                           |
| AI assist        | Claude Code for designated portions                 |

---

## Data: Two Corpora

Both corpora are synthetic, purpose-built JSON files. Schema is minimal and consistent
so both share the same indexing pipeline pattern.

### Corpus A — Product FAQ (`corpus_a_faq.json`)

**Late chunking should hurt.**

File: `corpus_a_faq.json` — 20 product FAQ entries for a fictional consumer electronics
brand. Entries span four product families: AcousticWave wireless headphones (M3–M7),
Nimbus Pro fitness trackers (Gen1–Gen5), Echo Sphere smart speakers (Mini/Plus/Pro/Max/
Ultra), and ArmorShield phone cases (S/M/X/Pro/Elite). Schema: `entry_id`, `category`,
`question`, `answer`.

Within each family, answers are near-identical in structure — same vocabulary, same
template — differing only in the specific distinguishing values (battery hours, warranty
months, weight, price). Adjacent items in the JSON array are from the same family.

When all 20 entries are passed as an array to the late-chunking inference endpoint, Jina
concatenates them and runs the full transformer over the sequence before pooling. Adjacent
family members — with nearly identical text — bleed context into each other's embeddings,
smoothing them toward a generic family centroid. A query for "AcousticWave M4 battery
life" finds the M4 embedding indistinguishable from the M3 and M5 embeddings.

### Corpus B — SEC 10-K Filings (`corpus_b_filing.json`)

**Late chunking should help.**

File: `corpus_b_filing.json` — 18 sections drawn from three fictional companies' SEC
10-K annual reports (6 sections each; `company_id` values `hayn`, `mwa`, `wts`). Schema:
`section_id`, `company_id`, `item`, `title`, `content`.

10-K filings are dense, cross-referential prose. Defined terms are introduced once
("the Company", "the Credit Facility", "the Allowance for Credit Losses") and referenced
throughout using those exact labels or pronouns. Sections build on prior sections —
risk factors reference business descriptions, MD&A references financial statements.
A section read in isolation frequently lacks the context needed to match a query that
uses the full term or concept name.

Standard per-chunk embedding captures only surface tokens. Late chunking embeds the
full filing as a single sequence, giving each section's vector access to document-level
context — defined terms, running narrative, and cross-section references are all resolved
before per-chunk pooling. **Late embeddings are computed one API call per company** so
each filing's context window stays isolated — this prevents one company's entities from
bleeding into another company's section vectors.

---

## Infrastructure: Terraform

Provision an Elastic Cloud Serverless Elasticsearch project.

### Resources

- Elastic Serverless project (type: `elasticsearch`, optimized for: `general_purpose`)
- Region: `gcp-us-central1` (default)
- Outputs: Elasticsearch URL, Kibana URL, Cloud ID
- After provisioning: create a scoped API key (not admin credentials) for notebook use

### File structure

```
terraform/
  elastic_serverless.tf
  variables.tf
  outputs.tf
  terraform.tfvars.sample
```

---

## Notebook: Structure

The notebook is the demo and the backbone of the article. It is readable as a
standalone narrative. Each section has a markdown cell describing what the code does.

### Sections

1. **Create Elastic Serverless Environment**
   - Terraform init + apply
   - Export credentials to `.env`

2. **Create Inference Endpoints**
   - Connect Elasticsearch client from `.env`
   - Create two EIS inference endpoints:
     - `jina-embeddings-v3-standard` — `jinaai` service, `late_chunking: False`, `input_type: search`
     - `jina-embeddings-v3-late` — `jinaai` service, `late_chunking: True`, `input_type: search`

3. **Load Indices**
   - Create four Elasticsearch indices (two per corpus):
     - `faq_standard` — Product FAQ, standard embedding (`semantic_text`, inference_id: jina-embeddings-v3-standard)
     - `faq_late` — Product FAQ, late chunking (`dense_vector`, pre-computed embeddings)
     - `filing_standard` — SEC 10-K Filings, standard embedding
     - `filing_late` — SEC 10-K Filings, late chunking
   - Ingest `corpus_a_faq.json` and `corpus_b_filing.json`
   - Filing late embeddings are grouped by `company_id` (one inference call per company)
   - Sample vectors + cosine printed to confirm standard and late embeddings differ
     (FAQ-001 cosine ≈ 0.62; wts_intro cosine ≈ 0.83)

4. **Retrieval & Measurement**
   - Load relevance judgments from `assets/judgments.json`
   - Run each query against both index variants per corpus
   - Standard index: `semantic` query via Elasticsearch
   - Late index: explicit vector embedding via `jina-embeddings-v3-late` inference endpoint → `knn` query
   - Metrics evaluated via Elasticsearch `_rank_eval` API at k=5:
     - **MRR** (Mean Reciprocal Rank)
     - **NDCG** (Normalized Discounted Cumulative Gain)

5. **Summary & Conclusions**
   - Decision rule for practitioners
   - Broader RAG system design implications

6. **Destroy Environment**
   - `terraform destroy`
   - Remove `.env`

---

## Results

Experiment is complete. Results confirmed the thesis on both sides.

### Corpus A — Product FAQ

| Metric | Standard | Late | Delta |
|--------|----------|------|-------|
| MRR    | 1.0000   | 0.5857 | −0.4143 |
| NDCG   | 0.9868   | 0.6161 | −0.3707 |

Standard embedding is essentially perfect. Late chunking degrades both metrics by ~40
points. Context bleed between adjacent near-identical FAQ entries dilutes the precise
per-chunk signal that makes standard embedding effective here.

### Corpus B — SEC 10-K Filings

| Metric | Standard | Late | Delta |
|--------|----------|------|-------|
| MRR    | 0.4028   | 0.7917 | +0.3889 |
| NDCG   | 0.5539   | 0.8462 | +0.2923 |

Standard embedding struggles — MRR of 0.40 means the correct chunk frequently isn't
the top result. Late chunking nearly doubles MRR and pushes NDCG above 0.84. Document-
level context resolution is essential for cross-referential financial prose.

---

## Article: Structure

The article (`assets/article.md`) is written. Title: **"Late Chunking Is a Tool, Not an
Upgrade."** Section flow:

1. **Intro** — What late chunking is, link to the 2024 Jina.ai blog, and the two-test-case framing.
2. **What This Article Covers** — Bulleted scope: Terraform provisioning, inference endpoints, indexing, rank evaluation.
3. **Architecture** — Notebook-driven Terraform + Elastic Serverless diagram.
4. **Create Elastic Environment** — Terraform spin-up, API keys via tfvars → `.env`.
5. **Inference Endpoints** — Standard vs. late endpoint config (with code snippet).
6. **Data Set** — Index table, schema notes, sample vectors + cosine output, per-company grouping note.
7. **Retrieval & Measurement** — Judgment list, MRR/NDCG metrics, query strategy, and per-corpus results.
8. **Conclusion** — Late chunking is not a free upgrade; takeaways keyed to data shape.
9. **Source** — Link to the GitHub repo.

---

## Task Breakdown

| #  | Task                                              | Status                                                    |
|----|---------------------------------------------------|-----------------------------------------------------------|
| 1  | Generate Corpus A (product FAQ JSON)              | Done — 20 entries, `corpus_a_faq.json`                    |
| 2  | Generate Corpus B (SEC 10-K filing JSON)          | Done — 18 sections, `corpus_b_filing.json`                |
| 3  | Confirm Jina v3 late chunking API details         | Done — array input, `late_chunking` boolean               |
| 4  | Build judgment list with graded ratings           | Done — `assets/judgments.json`                            |
| 5  | Write Terraform config                            | Done — `terraform/`                                       |
| 6  | Provision Elastic Serverless                      | Done — `terraform apply`                                  |
| 7  | Notebook: inference endpoint setup                | Done — standard + late endpoints created                  |
| 8  | Notebook: embedding helpers                       | Done — `faq.py`, `filing.py` in `late_chunking/`          |
| 9  | Notebook: index creation & ingestion              | Done — four indices, both corpora ingested                |
| 10 | Notebook: retrieval & measurement                 | Done — MRR + NDCG via `_rank_eval`                        |
| 11 | Run the experiment, evaluate results              | Done — results in hand (see Results section above)        |
| 12 | Notebook: markdown commentary                     | Done — all cells documented; summary/conclusions added    |
| 13 | Write the article                                 | Done — `assets/article.md`                                |
| 14 | Review & polish                                   | Done — spelling/grammar pass; results + conclusion edited |
