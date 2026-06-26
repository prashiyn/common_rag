COLLECTION_SCOPED_SECTION_QUERY = """
MATCH (c:Collection {id:$collection})
-[:HAS_DOCUMENT]->(d:Document)
-[:HAS_SECTION]->(s:Section)
OPTIONAL MATCH (s)-[:REFERS_TO*1..2]->(x)
RETURN s, x
"""

RESOLVE_DOCUMENTS_BY_QUARTER_QUERY = """
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.collection_id = $collection_id
  AND d.period = $period
  AND d.fiscal_year = $fiscal_year
RETURN d.id AS doc_id, d.timestamp AS timestamp
ORDER BY d.timestamp DESC, d.id ASC
"""

RESOLVE_DOCUMENTS_BY_FISCAL_YEAR_QUERY = """
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.collection_id = $collection_id
  AND d.fiscal_year = $fiscal_year
RETURN d.id AS doc_id, d.timestamp AS timestamp
ORDER BY d.timestamp DESC, d.id ASC
"""

RESOLVE_DOCUMENTS_BY_DATE_RANGE_QUERY = """
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.collection_id = $collection_id
  AND d.timestamp >= $start_date
  AND d.timestamp <= $end_date
RETURN d.id AS doc_id, d.timestamp AS timestamp
ORDER BY d.timestamp DESC, d.id ASC
"""

RESOLVE_LATEST_DOCUMENTS_QUERY = """
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.collection_id = $collection_id
RETURN d.id AS doc_id, d.timestamp AS timestamp
ORDER BY d.timestamp DESC, d.id ASC
"""

LIST_COLLECTIONS_QUERY = """
MATCH (c:Collection)
RETURN c.id AS id, coalesce(c.name, c.id) AS name
ORDER BY id ASC
"""

GET_COLLECTION_METADATA_QUERY = """
MATCH (c:Collection {id: $collection_id})
OPTIONAL MATCH (c)-[:HAS_DOCUMENT]->(d:Document)
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(ch:Chunk)
RETURN c.id AS id,
       coalesce(c.name, c.id) AS name,
       count(DISTINCT d) AS document_count,
       count(DISTINCT ch) AS chunk_count,
       min(d.timestamp) AS earliest_timestamp,
       max(d.timestamp) AS latest_timestamp
"""

LOAD_CHUNKS_FOR_DOC_IDS_QUERY = """
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)-[:HAS_CHUNK]->(ch:Chunk)
WHERE d.id IN $doc_ids
  AND d.collection_id = $collection_id
  AND ch.collection_id = $collection_id
OPTIONAL MATCH (ch)-[r:REFERS_TO]->(rt:ReferenceTarget)
WHERE rt.collection_id = $collection_id
  AND rt.document_id IN $doc_ids
WITH d, ch,
     [ref IN collect({
       reference_text: r.reference_text,
       reference_type: rt.reference_type,
       target_label: rt.label,
       confidence: r.confidence
     }) WHERE ref.reference_text IS NOT NULL] AS references
RETURN d.id AS document_id,
       ch.id AS chunk_id,
       ch.content AS content,
       ch.title_summary AS title_summary,
       ch.section_title AS section_title,
       ch.section_label AS section_label,
       ch.timestamp AS timestamp,
       references AS references
ORDER BY ch.timestamp DESC, ch.id ASC
"""

TRAVERSE_REFERENCE_MULTI_HOP_QUERY = """
MATCH (c:Collection {id: $collection_id})-[:HAS_DOCUMENT]->(d:Document)-[:HAS_CHUNK]->(src:Chunk)
WHERE d.id IN $doc_ids
  AND src.id IN $chunk_ids
  AND src.collection_id = $collection_id
OPTIONAL MATCH p=(src)-[:REFERS_TO*1..2]->(dst)
WHERE dst IS NULL OR (
    dst.collection_id = $collection_id
    AND (dst.document_id IS NULL OR dst.document_id IN $doc_ids)
)
RETURN d.id AS document_id,
       src.id AS source_chunk_id,
       coalesce(dst.id, "") AS target_chunk_id,
       coalesce(length(p), 0) AS hop_count
ORDER BY document_id ASC, source_chunk_id ASC, target_chunk_id ASC, hop_count ASC
"""

UPSERT_COLLECTION_QUERY = """
MERGE (c:Collection {id: $collection_id})
ON CREATE SET c.name = $collection_id
ON MATCH SET c.name = coalesce(c.name, $collection_id)
RETURN c
"""

UPSERT_DOCUMENT_QUERY = """
MERGE (d:Document {id: $document_id})
SET d.collection_id = $collection_id,
    d.fiscal_year = $fiscal_year,
    d.period = $period,
    d.timestamp = $timestamp
WITH d
MATCH (c:Collection {id: $collection_id})
MERGE (c)-[:HAS_DOCUMENT]->(d)
RETURN d
"""

UPSERT_CHUNK_QUERY = """
MERGE (ch:Chunk {id: $chunk_id})
SET ch.collection_id = $collection_id,
    ch.document_id = $document_id,
    ch.content = $content,
    ch.type = $chunk_type,
    ch.page = $page,
    ch.bundle_id = $bundle_id,
    ch.section_title = $section_title,
    ch.section_label = $section_label,
    ch.title_summary = $title_summary,
    ch.timestamp = $timestamp,
    ch.publish_date = $publish_date,
    ch.prev_chunk = $prev_chunk,
    ch.next_chunk = $next_chunk
WITH ch
MATCH (d:Document {id: $document_id})
MERGE (d)-[:HAS_CHUNK]->(ch)
RETURN ch
"""

UPSERT_SECTION_AND_LINK_CHUNK_QUERY = """
MERGE (s:Section {
  id: $section_id,
  document_id: $document_id,
  collection_id: $collection_id
})
SET s.label = $section_label,
    s.title = $section_title
WITH s
MATCH (d:Document {id: $document_id})
MERGE (d)-[:HAS_SECTION]->(s)
WITH s
MATCH (ch:Chunk {id: $chunk_id})
MERGE (ch)-[:IN_SECTION]->(s)
RETURN s
"""

UPSERT_REFERENCE_TARGET_AND_LINK_QUERY = """
MERGE (rt:ReferenceTarget {
  collection_id: $collection_id,
  document_id: $document_id,
  reference_type: $reference_type,
  label: $target_label
})
WITH rt
MATCH (ch:Chunk {id: $chunk_id})
MERGE (ch)-[r:REFERS_TO {
  reference_text: $reference_text,
  confidence: $confidence
}]->(rt)
RETURN rt
"""
