# Aktualizacja HF Space - Fix API Endpoint

## 🔴 PROBLEM
Hugging Face zmienił API endpoint:
- ❌ Stary: `https://api-inference.huggingface.co`
- ✅ Nowy: `https://router.huggingface.co`

## ✅ FIX
Zaktualizowałem `hf_space/app.py` (linia 36):
```python
# BYŁO:
f"https://api-inference.huggingface.co/models/{EMBEDDING_MODEL}"

# JEST:
f"https://router.huggingface.co/models/{EMBEDDING_MODEL}"
```

---

## 🚀 REDEPLOY HF SPACE

### Opcja A: Upload przez Web UI (SZYBCIEJ)

1. **Otwórz HF Space:**
   https://huggingface.co/spaces/TWOJA-NAZWA/mobby-rag-search-api

2. **Files tab → app.py → Edit**

3. **Zamień linię 36:**
   ```python
   f"https://router.huggingface.co/models/{EMBEDDING_MODEL}",
   ```

4. **Commit changes** (dół strony)

5. **Poczekaj ~30-60s** - HF Space automatycznie zrestartuje się

6. **Test:**
   ```bash
   curl https://mobby-rag-search-api.hf.space/health
   ```
   Powinno zwrócić `{"status": "healthy", "points": XXX}`

---

### Opcja B: Git Push (jeśli masz clone)

1. **Skopiuj poprawiony plik:**
   ```bash
   cp hf_space/app.py /path/to/hf-space-clone/app.py
   ```

2. **Commit & push:**
   ```bash
   cd /path/to/hf-space-clone
   git add app.py
   git commit -m "Fix HF API endpoint (api-inference → router)"
   git push
   ```

3. **HF Space auto-deploy** (~30-60s)

---

### Opcja C: Stwórz nowy HF Space (jeśli jeszcze nie masz)

1. **Otwórz:** https://huggingface.co/new-space

2. **Konfiguracja:**
   - Name: `mobby-rag-search-api`
   - SDK: **Docker** (wybierz z listy)
   - Hardware: **CPU basic** (free tier)

3. **Upload pliki z `hf_space/`:**
   - `app.py` (poprawiona wersja)
   - `requirements.txt`
   - `Dockerfile`

4. **Ustaw Secrets** (Settings → Variables):
   ```
   QDRANT_URL = https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io
   QDRANT_API_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0
   HF_TOKEN = hf_xxxxxxxxxxxxx (Twój token z https://huggingface.co/settings/tokens)
   ```

5. **Wait for build** (~2-3 min pierwszego razu)

6. **Nowy URL:**
   ```
   https://TWOJA-NAZWA-mobby-rag-search-api.hf.space
   ```

7. **Zaktualizuj n8n workflow:**
   W node "HTTP Request: RAG Search" zmień URL na nowy.

---

## 🧪 TEST PO UPDATE

### 1. Health check
```bash
curl https://mobby-rag-search-api.hf.space/health
```

**Oczekiwane:**
```json
{"status": "healthy", "points": 123}
```

### 2. Search test
```bash
curl -X POST https://mobby-rag-search-api.hf.space/search \
  -H "Authorization: Bearer hf_xxx" \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "top_k": 5}'
```

**Oczekiwane:**
```json
{
  "results": [
    {"title": "...", "text": "...", "url": "...", "score": 0.95}
  ],
  "query": "test"
}
```

### 3. n8n workflow test
```bash
curl -X POST https://ragme.app.n8n.cloud/webhook/rag-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Test po update"}'
```

---

## 🔍 TROUBLESHOOTING

### Space nie startuje
**Logs:** Kliknij **"Building"** → zobacz logs
**Fix:** Sprawdź czy `requirements.txt` i `Dockerfile` są OK

### 401 Error po update
**Problem:** Secrets nie są ustawione
**Fix:** Settings → Variables → dodaj `QDRANT_URL`, `QDRANT_API_KEY`, `HF_TOKEN`

### Nadal embedding error
**Problem:** Cache HF Space
**Fix:**
1. Settings → Factory Reboot
2. Poczekaj 2 min na restart

---

## ✅ GOTOWE

Po update HF Space, Twój n8n workflow powinien działać bez zmian!

Test workflow:
```bash
curl -X POST https://ragme.app.n8n.cloud/webhook/rag-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Jak używać agentów AI?"}'
```

Powodzenia! 🚀
