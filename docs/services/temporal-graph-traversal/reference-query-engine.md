# 📄 Reference-Aware Query Engine with Collections + Temporal Disambiguation (Final Spec)

---

## 🧠 1. Objective

Build a **Reference-Aware Query Engine (RAQE)** that:

- Works on **chunk-based ingestion (NOT document blobs)**
- Supports **collections (multi-document)**
- Handles **temporal reasoning**
- Resolves **cross-references accurately**
- Enables **multi-hop graph reasoning**

---

## 🧱 2. Input Data Model (CRITICAL UPDATE)

System operates on chunk-level content, but ingestion is grouped as:

`Collection -> Document -> [Chunk, Chunk, ...]`

Each document in a collection contains a list of chunks.

---

### Canonical Chunk Source of Truth (Implementation Note)

For implementation, `ChunkItem` in `docs/doc_processing_openapi.json` is the golden schema.

Required `ChunkItem` fields:

- `chunk_id`, `content`, `type`, `doc_id`, `page`, `bundle_id`
- `section_title`, `title_summary`, `publish_date`, `prev_chunk`, `next_chunk`
- `references` (optional array, each item is `ChunkReferenceItem`)

Required `ChunkReferenceItem` fields:

- `reference_text`, `reference_type`, `target_label`, `confidence`

RAQE-specific fields like `collection_id`, `section_id`, `section_label`, and normalized timestamp metadata must be derived/mapped during ingestion, not assumed to exist in raw `ChunkItem`.

---

### RAQE Normalized Chunk Schema (Post-Mapping)

```json
{
  "chunk_id": "uuid",
  "doc_id": "doc_1",
  "collection_id": "RELIANCE",
  "section_id": "sec_4.2",
  "section_label": "4.2",
  "timestamp": "2024-04-30",
  "content": "...",
  "references": [
    {
      "reference_text": "Table 3",
      "reference_type": "TABLE",
      "target_label": "3",
      "confidence": 0.95
    }
  ]
}
```

---

### Document Payload (Collection-Scoped, Chunk List)

```json
{
  "doc_id": "doc_1",
  "collection_id": "RELIANCE",
  "fiscal_year": "FY24",
  "period": "Q1",
  "timestamp": "2024-04-30",
  "chunks": [
    {
      "chunk_id": "uuid",
      "section_id": "sec_4.2",
      "section_label": "4.2",
      "timestamp": "2024-04-30",
      "content": "...",
      "references": []
    }
  ]
}
```

---

## 🔷 3. Core Concepts

### Collection
Logical grouping (company-level)

### Document
Time-bound entity (quarter/year)

### Chunk
Atomic unit of processing, always nested under one document

---

## 🔷 4. Graph Schema (Neo4j)

### Nodes

```cypher
(:Collection {id, name})

(:Document {
  id,
  collection_id,
  fiscal_year,
  period,
  timestamp
})

(:Chunk {
  id,
  document_id,
  collection_id,
  section_id,
  section_label,
  timestamp
})

(:Section {
  id,
  label,
  document_id,
  collection_id
})

(:Table {
  id,
  label,
  document_id,
  collection_id
})

(:Event {id, timestamp})
```

---

### Relationships

```cypher
(Collection)-[:HAS_DOCUMENT]->(Document)

(Document)-[:HAS_CHUNK]->(Chunk)

(Document)-[:HAS_SECTION]->(Section)

(Chunk)-[:IN_SECTION]->(Section)

(Section)-[:CONTAINS]->(Table)

(Section)-[:REFERS_TO]->(Table)

(Event)-[:MENTIONED_IN]->(Section)
```

---

## 🔷 5. Query Flow (UPDATED)

```text
Query
 → parse_query()
 → parse_time()
 → identify collection
 → resolve_documents()
 → load document chunk lists
 → filter chunks
 → build_plan()
 → execute_plan()
 → traverse references
 → build context
 → generate answer
```

---

## 🔷 6. Document Resolution

```python
def resolve_documents(collection, time_context):
    return []
```

---

## 🔷 7. Chunk Filtering (NEW)

```python
def filter_chunks(collection, doc_ids):
    return []
```

---

## 🔷 8. Reference Resolution (UPDATED)

```python
def resolve_reference(ref, collection, doc_ids):
    return None
```

---

### Logic

```text
1. Filter by collection_id
2. Filter by document_id
3. Match label (Table 3 → label=3)
4. If multiple:
   → use section proximity
   → use graph distance
```

---

## 🔷 9. Scoped Neo4j Query

```cypher
MATCH (c:Collection {name:$collection})
-[:HAS_DOCUMENT]->(d:Document)
WHERE d.id IN $doc_ids

MATCH (d)-[:HAS_CHUNK]->(ch:Chunk)-[:IN_SECTION]->(s:Section)

OPTIONAL MATCH (s)-[:REFERS_TO*1..2]->(x)

RETURN d, ch, s, x
```

---

## 🔷 10. Temporal Reasoning + Disambiguation

### Problem

```text
Table 3 exists in multiple documents
```

---

### Solution

All resolution must use:

```text
(collection_id + document_id + label)
```

---

### Disambiguation Logic

```python
def disambiguate(nodes, context):
    return nodes
```

---

### Rules

1. Same document > others  
2. Closest section > distant  
3. Latest timestamp > older  
4. Highest confidence  

---

## 🔷 11. Execution Engine (UPDATED)

```python
def execute_plan(plan, query):
    docs = resolve_documents(query["collection"], query["time"])
    chunks = filter_chunks(query["collection"], docs)

    events = fetch_events(chunks)
    refs = traverse_references(chunks)
    tables = fetch_tables(refs)

    return {
        "events": events,
        "references": refs,
        "tables": tables
    }
```

---

## 🔷 12. Context Builder

Must include:

- collection_id
- document_id  
- fiscal period  
- chunk_id
- section context  

---

### Example

```text
Document: Q1 FY24

Section 4.2:
- Revenue increased

Reference:
- Table 3

Data:
- 2023: 100
- 2024: 120
```

---

## 🔷 13. Cursor Instructions

```text
1. Update ingestion to store documents with chunk lists
2. Preserve hierarchy: Collection -> Document -> Chunks
3. Add collection_id to all relevant nodes
4. Add document_id to all relevant nodes, including chunks
5. Implement time_resolver
6. Implement chunk filtering layer from resolved doc_ids
7. Update resolver to use collection + document scope
8. Update graph queries to filter by doc_ids and traverse document chunks
9. Add disambiguation logic
10. Update query engine flow
```

---

## 🔷 14. Final Flow

```text
Collection -> Document -> Chunks
      -> Graph (Structure + Reference)
      → Query Engine
      → Temporal + Disambiguation
      → Answer
```

---

## 🧠 Final Insight

System is now:

→ Chunk-aware  
→ Document-aware  
→ Collection-aware  
→ Time-aware  
→ Reference-aware  

---

## 🚀 Next Step

Backtesting + signal validation layer
