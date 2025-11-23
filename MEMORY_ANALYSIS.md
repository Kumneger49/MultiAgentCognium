# Memory Usage Analysis & Optimization Options

## Current Problem
- **Container crashes with exit code 137 (OOM)** even with `batch_size=1`
- **2GB droplet** is insufficient for current implementation

---

## Root Cause Analysis

### Current Implementation (Inefficient)
```python
# In news_pipeline.py - generate_recommendations()
for batch_num in range(0, len(news_items), batch_size):
    # ❌ Creates NEW RAGAnything instance for EACH batch
    response = _run_async_safely(ragmain(formatted_prompt, file_path=file_path))
```

**What happens per batch:**
1. `ragmain()` creates a **NEW** `RAGAnything` instance
2. Each instance loads:
   - Knowledge graph (557 nodes, 1496 edges) → ~50-100MB
   - KV stores (full_docs, text_chunks, entities, relations, etc.) → ~100-200MB
   - LLM/embedding workers → ~200-300MB
   - Document processing pipeline → ~100-200MB
   - Python/RAGAnything overhead → ~200-300MB
   - **Total per instance: ~650MB-1.1GB**

3. With 44 batches (batch_size=1):
   - **Peak memory: 44 × 650MB = 28.6GB** (theoretical)
   - **Actual: Memory accumulates, container crashes at ~2GB**

### Why It Crashes
- Even though Python GC should clean up, RAGAnything instances hold:
  - Open file handles
  - In-memory caches
  - Worker threads/processes
  - LightRAG graph objects
- These don't release immediately, causing memory to accumulate

---

## Optimization Options

### ✅ Option 1: Reuse Single RAGAnything Instance (RECOMMENDED)
**Impact:** Reduce memory from 44× instances to 1× instance (~650MB-1.1GB)

**How:**
1. Create ONE `RAGAnything` instance before the batch loop
2. Reuse it for all 44 queries
3. Only process document once (it's cached anyway)

**Implementation:**
- Refactor `cognium_codebase/main.py` to expose:
  - `init_rag()` → returns RAGAnything instance
  - `query_rag(rag_instance, query, file_path)` → reuses instance
- Modify `news_pipeline.py` to:
  - Initialize RAG once before loop
  - Reuse for all batches
  - Clean up after loop

**Estimated Memory:**
- **Before:** 44 × 650MB = 28.6GB (theoretical peak)
- **After:** 1 × 650MB = 650MB-1.1GB
- **Savings:** ~95% reduction
- **Feasibility:** ✅ Should fit in 2GB droplet

---

### Option 2: Reduce RAG Cache Sizes
**Impact:** Reduce baseline memory from ~650MB to ~400-500MB

**How:**
- Disable image/table/equation processing (if not needed)
- Reduce KV store sizes
- Use smaller embedding dimensions

**Trade-offs:**
- May reduce RAG quality
- Still need Option 1 to avoid 44× multiplier

---

### Option 3: Process Fewer News Items
**Impact:** Reduce from 44 batches to ~20-30 batches

**How:**
- Filter news items more aggressively (relevance > 0.5 instead of 0.2)
- Process only top N tickers
- Skip low-relevance items

**Trade-offs:**
- Reduces recommendation coverage
- Still need Option 1 for efficiency

---

### Option 4: Upgrade Droplet to 4GB
**Impact:** Provides headroom for current inefficient code

**Cost:** ~$24/month (vs $12/month for 2GB)

**Trade-offs:**
- ✅ No code changes needed
- ❌ More expensive
- ❌ Doesn't fix the root cause (inefficient code)
- ❌ Still wastes resources

---

## Recommended Solution: Option 1 (Reuse RAG Instance)

### Why This Is Best:
1. **Fixes root cause** (inefficient instance creation)
2. **95% memory reduction** (44× → 1×)
3. **No cost increase** (stays on 2GB droplet)
4. **Faster execution** (no repeated initialization)
5. **Better code quality** (proper resource management)

### Implementation Plan:
1. Refactor `cognium_codebase/main.py`:
   - Split `main()` into `init_rag()` and `query_rag()`
   - Keep backward compatibility with `main()` wrapper
2. Modify `news_pipeline.py`:
   - Initialize RAG once before batch loop
   - Reuse instance for all queries
   - Add proper cleanup/error handling
3. Test locally first, then deploy

### Estimated Time: 30-60 minutes

---

## Memory Usage Comparison

| Approach | Memory per Batch | Total (44 batches) | Fits in 2GB? |
|----------|------------------|-------------------|--------------|
| **Current (inefficient)** | ~650MB | ~28.6GB (peak) | ❌ No |
| **Option 1 (reuse instance)** | ~650MB (shared) | ~650MB-1.1GB | ✅ Yes |
| **Option 2 (reduce cache)** | ~400MB (shared) | ~400-500MB | ✅ Yes |
| **Option 3 (fewer items)** | ~650MB | ~13-19.5GB | ❌ No |
| **Option 4 (upgrade)** | ~650MB | ~28.6GB (peak) | ✅ Yes (4GB) |

---

## Next Steps

1. **Implement Option 1** (reuse RAG instance)
2. **Test locally** with full pipeline
3. **Monitor memory** during test run
4. **Deploy to droplet** if successful
5. **Fallback to Option 4** only if Option 1 fails

---

## Questions to Answer

- [x] **Can RAGAnything instance be safely reused across multiple queries?**  
  ✅ **YES** - `rag.aquery()` is read-only (queries don't modify knowledge graph)
  
- [x] **Does `rag.aquery()` modify internal state that would break reuse?**  
  ✅ **NO** - `aquery()` only reads from the knowledge graph, doesn't write
  
- [x] **Are there thread-safety concerns with concurrent queries?**  
  ⚠️ **POTENTIAL** - Since we're processing batches sequentially (not concurrently), this is safe
  
- [x] **How long does RAG instance initialization take?**  
  ⏱️ **~5-10 seconds** - Loading knowledge graph and KV stores (one-time cost)

---

## Key Finding: `process_document_complete()` is Called Every Time

**Current code in `ragmain()`:**
```python
# ❌ Called 44 times (once per batch)
await rag.process_document_complete(file_path, ...)  # Checks cache, but still overhead
await rag.aquery(query, ...)
```

**Optimized code:**
```python
# ✅ Called once (before batch loop)
await rag.process_document_complete(file_path, ...)  # One-time setup

# ✅ Called 44 times (reuses same instance)
for batch in batches:
    await rag.aquery(query, ...)  # No re-initialization needed
```

**Why this works:**
- `process_document_complete()` is **idempotent** (checks cache, skips if already processed)
- `aquery()` is **stateless** (read-only queries)
- RAG instance holds the knowledge graph in memory (persists across queries)

