# 🚀 RAG Quick Start - Opcja 1 (HF Inference API)

**100% FREE TIER | 5 minut setup | Zero deployment**

---

## ✅ Czego potrzebujesz?

| Co | Gdzie dostać | Koszt |
|----|--------------|-------|
| **HF Token** | https://huggingface.co/settings/tokens | FREE (1000 req/dzień) |
| **Qdrant** | Masz już! | FREE (1GB) |
| **OpenRouter** | https://openrouter.ai/keys | FREE ($5 start) |
| **n8n** | Twoja instancja | FREE tier |

---

## 📝 KROK 1: Zdobądź tokeny

### HF Token (jeśli nie masz)
```bash
1. Otwórz: https://huggingface.co/settings/tokens
2. Click: "New token"
3. Name: "n8n-rag-embedding"
4. Type: Read
5. Click: Generate
6. Copy: hf_xxxxxxxxxxxxx
```

### OpenRouter API Key (jeśli nie masz)
```bash
1. Otwórz: https://openrouter.ai/keys
2. Click: "Create API Key"
3. Name: "n8n-rag-llm"
4. Copy: sk-or-v1-xxxxxxxxxxxxx
```

### Qdrant credentials (już masz!)
```
QDRANT_URL=https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0
```

---

## 🔧 KROK 2: n8n Environment Variables

1. **Otwórz n8n** w przeglądarce
2. **Settings → Environments → Variables**
3. **Dodaj 4 zmienne:**

```env
HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
QDRANT_URL=https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxx
```

4. **Save**

---

## 📥 KROK 3: Import workflow

1. **n8n → Workflows** (górny menu)
2. **Click: "Import from File"**
3. **Wybierz plik:** `n8n_workflow_direct_qdrant.json`
4. **Click: Import**
5. **Workflow się załaduje** - zobaczysz 10 nodes
6. **Ctrl+S / Cmd+S** (zapisz)

---

## ⚡ KROK 4: Aktywuj workflow

1. **Toggle "Active" ON** (prawy górny róg - przełącznik)
2. **Kliknij node:** "Webhook: RAG Question"
3. **Skopiuj Production URL:**
   ```
   https://TWOJA-INSTANCJA.app.n8n.cloud/webhook/rag-agent
   ```

---

## 🧪 KROK 5: Test

### Test 1: HF Inference API

Przed uruchomieniem workflow, sprawdź czy HF API działa:

```bash
# 1. Edytuj plik test_hf_api.sh
nano test_hf_api.sh

# 2. Zmień linię 12:
HF_TOKEN="hf_YOUR_REAL_TOKEN_HERE"

# 3. Uruchom test:
bash test_hf_api.sh
```

**Oczekiwany output:**
```
✅ SUCCESS! HF Inference API działa!
Embedding wymiary: ~768
✅ Możesz teraz użyć workflow w n8n!
```

### Test 2: Pełny workflow (n8n)

```bash
curl -X POST https://TWOJA-INSTANCJA.app.n8n.cloud/webhook/rag-agent \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Jak używać agentów AI w developmencie?"
  }'
```

**Oczekiwana odpowiedź:**
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

## 🎯 Workflow Flow

```
┌─────────────────────────────────────────────────┐
│ 1. Webhook                                      │
│    Otrzymuje pytanie użytkownika                │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 2. AI Agent: Analyze Question                   │
│    OpenRouter - określa top_k (10-15)           │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 3. HTTP: Generate Embedding                     │
│    HF Inference API - nomic-embed-text-v1.5     │
│    → zwraca vector[768]                         │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 4. Code: Prepare Qdrant Query                   │
│    Buduje JSON query dla Qdrant                 │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 5. HTTP: Qdrant Search                          │
│    Wyszukuje w bazie (7725 punktów)             │
│    → zwraca top 10-15 wyników                   │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 6. Code: Format Qdrant Results                  │
│    Formatuje wyniki jako kontekst               │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 7. AI Agent: Generate Answer                    │
│    OpenRouter - generuje odpowiedź po polsku    │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│ 8. Respond to Webhook                           │
│    Zwraca JSON z odpowiedzią + źródłami         │
└─────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### Problem: "401 Unauthorized" z HF API

**Przyczyna:** Niepoprawny HF_API_TOKEN

**Fix:**
1. Sprawdź czy token w n8n Environments jest poprawny
2. Wygeneruj nowy token: https://huggingface.co/settings/tokens
3. Upewnij się że token zaczyna się od `hf_`

### Problem: "503 Service Unavailable" z HF API

**Przyczyna:** Model loading (cold start)

**Fix:**
- To normalne przy pierwszym użyciu
- Poczekaj 30-60 sekund
- Spróbuj ponownie - następne requesty będą szybkie

### Problem: "Empty results" z Qdrant

**Przyczyna:** Baza pusta lub score_threshold za wysoki

**Fix:**
1. Sprawdź liczbę punktów:
   ```bash
   python main.py info
   ```
2. Jeśli 0 → uruchom ingestię:
   ```bash
   python main.py ingest --recreate
   ```
3. W workflow node "Code: Prepare Qdrant Query" zmień:
   ```javascript
   score_threshold: 0.3  // zamiast 0.5
   ```

### Problem: Workflow nie startuje w n8n

**Przyczyna:** Brakujące zmienne środowiskowe

**Fix:**
1. n8n → Settings → Environments
2. Sprawdź czy wszystkie 4 zmienne są ustawione:
   - HF_API_TOKEN
   - QDRANT_URL
   - QDRANT_API_KEY
   - OPENROUTER_API_KEY
3. Toggle workflow OFF → ON

---

## 📊 Statystyki FREE Tier

| Serwis | Limit | Wystarczy na |
|--------|-------|--------------|
| **HF Inference API** | 1000 req/dzień | ~30k req/miesiąc |
| **Qdrant Cloud** | 1GB storage | ~50k dokumentów |
| **OpenRouter** | $5 credit | ~500-1000 requestów |
| **n8n Cloud** | 5k executions/m | Wystarczy do testów |

**Koszt miesięczny:** 0 zł (na start)

---

## 🎉 CO DALEJ?

### Masz działający RAG! Teraz możesz:

1. **Integracja z frontendem**
   - Dodaj prostą stronę HTML z formularzem
   - Wywołuj webhook przez fetch/axios
   - Wyświetlaj odpowiedzi i źródła

2. **Dodaj więcej artykułów**
   ```bash
   # Nowy export z WordPress
   python main.py ingest --resume
   ```

3. **Ulepszenia workflow**
   - Dodaj cache dla pytań (Redis/SQLite)
   - Włącz ColBERT reranking (search.py ma już kod)
   - Dodaj filtry po tagach/datach

4. **Monitoring**
   - n8n Executions → zobacz logi wszystkich wywołań
   - Qdrant Dashboard → statystyki wyszukiwania

---

## ✅ Podsumowanie

**Co masz:**
- ✅ Workflow bez HF Space (zero deployment!)
- ✅ 7725 dokumentów w Qdrant Cloud
- ✅ Embeddingi przez HF Inference API (FREE)
- ✅ LLM przez OpenRouter (FREE start credit)
- ✅ Wszystko w n8n (łatwe modyfikacje)

**Co NIE potrzebujesz:**
- ❌ app.py (nie używany!)
- ❌ HF Space deployment
- ❌ Dockerfile
- ❌ requirements.txt dla HF Space

**Możesz usunąć cały folder `hf_space/`** - nie jest potrzebny w Opcji 1!

---

**Gotowe! 🚀**

Masz pytania? Sprawdź:
- `DIRECT_QDRANT_SETUP.md` - szczegółowy opis architektury
- `README.md` - dokumentacja projektu
- `CONVERSATION_LOG.md` - historia zmian
