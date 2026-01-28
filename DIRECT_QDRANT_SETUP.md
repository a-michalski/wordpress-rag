# RAG Workflow - Bezpośrednie Qdrant (BEZ HF Space!)

## ✅ CO SIĘ ZMIENIŁO?

### BYŁO (z HF Space):
```
n8n → HF Space → [Embedding + Qdrant] → n8n → LLM
```
- ❌ Deployment HF Space
- ❌ 2 warstwy (n8n + HF Space)
- ❌ Modyfikacje = rebuild HF Space

### JEST (bez HF Space):
```
n8n → HF Inference API (embedding) → Qdrant → n8n → LLM
```
- ✅ Zero deployment!
- ✅ 1 warstwa (tylko n8n)
- ✅ Modyfikacje = edit workflow w n8n

---

## 🚀 INSTALACJA

### 1. Environment Variables w n8n

**Settings → Environments → Add Variables:**

```bash
QDRANT_URL=https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0
HF_API_TOKEN=hf_xxxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx
```

**Gdzie dostać tokeny:**
- **QDRANT_URL & API_KEY**: Masz już w `config.py`
- **HF_API_TOKEN**: https://huggingface.co/settings/tokens
- **OPENROUTER_API_KEY**: https://openrouter.ai/keys

---

### 2. Import Workflow

1. n8n → **Import from File**
2. Wybierz: `n8n_workflow_direct_qdrant.json`
3. Kliknij **Import**
4. ✅ Gotowe!

---

### 3. Aktywuj Workflow

1. Toggle **"Active"** (góra workflow)
2. Sprawdź czy webhook ma URL (kliknij Webhook node)

---

## 🧪 TEST

### Webhook URL
```
https://TWOJA-INSTANCJA.app.n8n.cloud/webhook/rag-agent
```

### Test request
```bash
curl -X POST https://ragme.app.n8n.cloud/webhook/rag-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Jak używać agentów AI w developmencie?"}'
```

### Oczekiwana odpowiedź
```json
{
  "question": "Jak używać agentów AI w developmencie?",
  "answer": "Na podstawie znalezionych artykułów...",
  "sources": [
    {"title": "...", "url": "...", "score": 0.95}
  ],
  "sources_count": 8,
  "has_results": true
}
```

---

## 📊 STRUKTURA WORKFLOW

```
┌────────────────────┐
│ Webhook            │ {"question": "..."}
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ AI Agent:          │ Analizuje pytanie
│ Analyze Question   │ Określa top_k
│ (OpenRouter)       │ Temp: 0.3
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ HTTP: Generate     │ HF Inference API
│ Embedding          │ nomic-ai model
│                    │ → zwraca vector[768]
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ Code: Prepare      │ Buduje query dla
│ Qdrant Query       │ Qdrant API
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ HTTP: Qdrant       │ POST /points/search
│ Search             │ Auth: api-key
│                    │ → zwraca results
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ Code: Format       │ Parsuje Qdrant
│ Results            │ Buduje kontekst
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ AI Agent:          │ Generuje odpowiedź
│ Generate Answer    │ Po polsku + źródła
│ (OpenRouter)       │ Temp: 0.5
└──────┬─────────────┘
       ▼
┌────────────────────┐
│ Response           │ JSON output
└────────────────────┘
```

---

## 🔍 KLUCZOWE ENDPOINTY

### 1. HF Router API (Embedding)
```
POST https://router.huggingface.co/models/nomic-ai/nomic-embed-text-v1.5

Headers:
  Authorization: Bearer {HF_API_TOKEN}
  Content-Type: application/json

Body:
  {"inputs": "search_query: pytanie użytkownika"}

Response:
  [[0.123, 0.456, ...]]  // 768-dim array
```

---

### 2. Qdrant Search API
```
POST {QDRANT_URL}/collections/wordpress_articles/points/search

Headers:
  api-key: {QDRANT_API_KEY}
  Content-Type: application/json

Body:
  {
    "vector": {
      "name": "dense",
      "vector": [0.123, 0.456, ...]
    },
    "limit": 10,
    "with_payload": true,
    "score_threshold": 0.5
  }

Response:
  {
    "result": [
      {
        "id": "uuid",
        "score": 0.95,
        "payload": {
          "title": "...",
          "text": "...",
          "url": "...",
          "tags": [...],
          "section_type": "content"
        }
      }
    ]
  }
```

---

## ⚡ ZALETY NOWEJ ARCHITEKTURY

| Aspekt | Stara (HF Space) | Nowa (Direct) |
|--------|-----------------|---------------|
| Deployment | ❌ Rebuild HF Space | ✅ Zero deployment |
| Modyfikacje | ❌ Git push + wait | ✅ Edit w n8n (instant) |
| Warstwy | ❌ 2 (n8n + HF) | ✅ 1 (tylko n8n) |
| Secrets | ⚠️ 2 miejsca | ✅ 1 miejsce (n8n) |
| Szybkość | ~500-1000ms | ~300-500ms ✅ |
| Koszt | HF Space hosting? | **FREE** ✅ |
| Debug | ❌ Logs w 2 miejscach | ✅ Wszystko w n8n |

---

## 🐛 TROUBLESHOOTING

### Problem: "Embedding error" z HF API
**Przyczyna:** Niepoprawny HF_API_TOKEN lub model unavailable

**Fix:**
1. Sprawdź token: https://huggingface.co/settings/tokens
2. Test API:
   ```bash
   curl https://router.huggingface.co/models/nomic-ai/nomic-embed-text-v1.5 \
     -H "Authorization: Bearer hf_xxx" \
     -H "Content-Type: application/json" \
     -d '{"inputs": "test"}'
   ```
3. Jeśli 503 - model loading, poczekaj 30s

---

### Problem: "Qdrant connection error"
**Przyczyna:** QDRANT_URL lub QDRANT_API_KEY niepoprawny

**Fix:**
1. Sprawdź credentials w `config.py`
2. Test Qdrant:
   ```bash
   curl https://79a7ee05...qdrant.io/collections/wordpress_articles \
     -H "api-key: YOUR_KEY"
   ```
3. Powinno zwrócić collection info

---

### Problem: "Empty results" z Qdrant
**Przyczyna:** Baza pusta lub score_threshold za wysoki

**Fix:**
1. Sprawdź czy są punkty:
   ```bash
   python main.py info
   ```
2. Jeśli 0 points → uruchom ingestię:
   ```bash
   python main.py ingest --recreate
   ```
3. W workflow → zmniejsz `score_threshold: 0.3` (w Code: Prepare Query)

---

## 📝 CO USUNĄĆ?

Jeśli używasz nowego workflow, **możesz usunąć:**

- ❌ Cały folder `hf_space/` (niepotrzebny!)
- ❌ HF Space deployment (jeśli był)
- ❌ `HF_SPACE_UPDATE.md` (nieaktualne)
- ❌ Stary workflow `n8n_workflow_fixed.json`

**Zostaw:**
- ✅ `n8n_workflow_direct_qdrant.json` (nowy!)
- ✅ `DIRECT_QDRANT_SETUP.md` (ta instrukcja)
- ✅ Lokalne pliki RAG (`search.py`, `embeddings.py` etc.)

---

## 🎯 NASTĘPNE KROKI

### Opcjonalne ulepszenia:

1. **Dodaj cache** - zapisuj embeddingi pytań (Redis/SQLite)
2. **Batch queries** - wiele pytań jednocześnie
3. **Reranking** - użyj ColBERT (jak w `search.py`)
4. **Filtry** - dodaj tags/dates (modyfikuj Qdrant query)

Jeśli chcesz któreś z tych - daj znać!

---

## ✅ PODSUMOWANIE

**Nowy workflow:**
- ✅ **12 nodes** (vs 11 poprzednio)
- ✅ **Zero deployment** (vs HF Space rebuild)
- ✅ **2 HTTP calls** (Embedding + Qdrant)
- ✅ **Wszystko w n8n** (łatwe modyfikacje)

**Import → Set env variables → Active → Gotowe!** 🚀
