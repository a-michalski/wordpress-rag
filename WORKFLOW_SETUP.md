# Setup Workflow RAG w n8n - Instrukcja

## ✅ GOTOWY WORKFLOW

**Plik:** `n8n_workflow_fixed.json`

**Co zostało naprawione:**
- ✅ `baseURL: "https://openrouter.ai/api/v1"` w obu OpenRouter nodes
- ✅ Credentials używają `$env.OPENROUTER_API_KEY` zamiast hardcoded ID
- ✅ Oczyszczone nazwy (bez "1")
- ✅ Error handling dla RAG API
- ✅ Sources array w response
- ✅ Temperature: 0.3 (Analyze), 0.5 (Answer)

---

## 🚀 INSTALACJA

### Krok 1: Ustaw Environment Variables w n8n

**Settings → Environments → Add Variables:**

```bash
HF_API_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx
```

**Gdzie dostać tokeny:**
- **HF_API_TOKEN**: https://huggingface.co/settings/tokens
- **OPENROUTER_API_KEY**: https://openrouter.ai/keys

---

### Krok 2: Importuj workflow

1. Otwórz n8n
2. **Import from File** → wybierz `n8n_workflow_fixed.json`
3. Workflow się załaduje automatycznie

---

### Krok 3: Skonfiguruj OpenRouter Credentials

**WAŻNE:** n8n może pokazać błąd credentials. Napraw to:

1. Kliknij **"OpenRouter: Analyze Model"**
2. W panelu po prawej → **Credentials**
3. Jeśli pokazuje błąd:
   - Kliknij "Create New Credential"
   - Type: **OpenAI API**
   - Name: **OpenRouter API**
   - API Key: `={{$env.OPENROUTER_API_KEY}}`
   - Save
4. Powtórz dla **"OpenRouter: Answer Generator"**

---

### Krok 4: Aktywuj workflow

1. Kliknij **"Active"** toggle (góra)
2. Workflow powinien być zielony

---

## 🧪 TEST WORKFLOW

### Webhook URL

```
https://TWOJA-INSTANCJA.app.n8n.cloud/webhook/rag-agent
```

Znajdziesz w node **"Webhook: RAG Question"** → **Test URL**

### Przykładowy request

```bash
curl -X POST https://ragme.app.n8n.cloud/webhook/rag-agent \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Jak używać agentów AI w developmencie?"
  }'
```

### Oczekiwana odpowiedź

```json
{
  "question": "Jak używać agentów AI w developmencie?",
  "answer": "Na podstawie znalezionych artykułów...\n\n**Źródła:**\n- [Tytuł](URL)",
  "sources": [
    {"title": "...", "url": "...", "score": 0.95}
  ],
  "sources_count": 8,
  "has_results": true
}
```

---

## 🔍 STRUKTURA WORKFLOW

```
┌─────────────────┐
│ Webhook         │ Przyjmuje {"question": "..."}
└────────┬────────┘
         ▼
┌─────────────────┐
│ AI Agent:       │ Analizuje pytanie
│ Analyze         │ Określa top_k (10-15)
│ (Claude 3.5)    │ Temp: 0.3
└────────┬────────┘
         ▼
┌─────────────────┐
│ HTTP Request:   │ Wysyła do HF Space
│ RAG Search      │ Auth: HF_API_TOKEN
│                 │ Body: {query, top_k}
└────────┬────────┘
         ▼
┌─────────────────┐
│ Check Errors    │ Waliduje response
│                 │ Obsługuje błędy
└────────┬────────┘
         ▼
┌─────────────────┐
│ Format Context  │ Przetwarza wyniki
│                 │ Buduje kontekst
└────────┬────────┘
         ▼
┌─────────────────┐
│ AI Agent:       │ Generuje odpowiedź PL
│ Generate        │ Z cytatami źródeł
│ (Claude 3.5)    │ Temp: 0.5
└────────┬────────┘
         ▼
┌─────────────────┐
│ Response        │ JSON z answer + sources
└─────────────────┘
```

---

## ⚙️ KONFIGURACJA MODELI

### Domyślny model
```
anthropic/claude-3.5-sonnet
```

### Alternatywy (zmień w OpenRouter nodes):

**Szybsze/tańsze:**
- `openai/gpt-4o-mini`
- `google/gemini-2.0-flash-exp`

**Lepsze/droższe:**
- `anthropic/claude-3-opus`
- `openai/gpt-4-turbo`

**Darmowe (wolniejsze):**
- `google/gemini-pro-1.5`

---

## 🐛 TROUBLESHOOTING

### Błąd: "401 Unauthorized" (OpenRouter)
**Przyczyna:** Brak baseURL lub niepoprawny API key

**Fix:**
1. Sprawdź czy `OPENROUTER_API_KEY` jest ustawiony
2. Sprawdź czy OpenRouter nodes mają `baseURL: "https://openrouter.ai/api/v1"`
3. Zweryfikuj API key na https://openrouter.ai/keys

---

### Błąd: "Connection timeout" (HF Space)
**Przyczyna:** HF Space śpi (cold start) lub nie odpowiada

**Fix:**
1. Sprawdź czy `HF_API_TOKEN` jest poprawny
2. Otwórz https://mobby-rag-search-api.hf.space w przeglądarce (obudzi Space)
3. Poczekaj 30s i spróbuj ponownie

---

### Błąd: "No results found"
**Przyczyna:** Pytanie nie pasuje do artykułów w bazie

**Fix:**
1. Sprawdź czy Qdrant ma dane: `python main.py info`
2. Przeformułuj pytanie (bardziej ogólne)
3. Zwiększ `top_k` w Code Tool (do 20)

---

### Response zwraca `has_results: false`
**Przyczyna:** HF API nie znalazł wyników lub błąd

**Fix:**
1. Sprawdź execution log w n8n (kliknij execution → debug)
2. Zobacz co zwrócił "HTTP Request: RAG Search"
3. Jeśli error - sprawdź HF Space logs

---

## 📊 MONITORING

### Koszty OpenRouter
Sprawdzaj: https://openrouter.ai/activity

**Przeciętne koszty:**
- 1 request = ~5000 tokenów
- Claude 3.5 Sonnet: $0.015/request (~1.5 grosza)
- 1000 requestów/dzień = $15/dzień

**Zmniejszanie kosztów:**
- Użyj `gpt-4o-mini` ($0.003/request)
- Zmniejsz top_k (mniej kontekstu)
- Cache odpowiedzi (dodaj Redis)

---

## 🔐 BEZPIECZEŃSTWO

### ⚠️ NIGDY nie commituj
```
# .gitignore
.env
*_workflow_*.json  # workflow może zawierać secrets
```

### ✅ Używaj env variables
Wszystkie API keys w `$env.XXX`, nigdy hardcoded!

---

## 📝 SUMMARY

**11 nodes:**
1. Webhook
2. AI Agent: Analyze
3. OpenRouter: Analyze Model
4. Code Tool: Parameters
5. Structured Output Parser
6. HTTP Request: RAG Search
7. Code: Check Errors
8. Code: Format Context
9. AI Agent: Generate Answer
10. OpenRouter: Answer Generator
11. Respond to Webhook

**MVP bez filtrów:**
- ✅ Szybkie (bez redeploy HF Space)
- ✅ Działa od razu
- ⚠️ Bez filtrów (tags, dates, categories)
- 💡 LLM kompensuje w kontekście

**Przyszłość:**
Jeśli potrzebujesz filtrów → update `hf_space/app.py` (powiedz mi!)

---

Gotowe! 🚀
