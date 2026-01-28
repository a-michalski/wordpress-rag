# Analiza N8N Workflow - RAG Agent

## 📊 OCENA OGÓLNA: **7.5/10**

Solidny workflow z dobrą architekturą, ale wymaga kilku poprawek technicznych.

---

## ✅ MOCNE STRONY

### 1. Architektura (9/10)
**Struktura node'ów jest prawidłowa:**
- ✅ Webhook → AI Agent → RAG API → Format → LLM → Response
- ✅ Używa Google Gemini (dobry wybór, szybki i tani)
- ✅ **2 osobne agenty**: jeden do analizy pytania, drugi do generowania odpowiedzi
- ✅ Structured Output Parser dla walidacji JSON

### 2. Logika Agenta (8/10)
**Code Tool "Build RAG Parameters" robi inteligentne mapowanie:**

```javascript
// ✅ Wykrywa "najnowsze" → date_range (ostatnie 6 miesięcy)
if (lowerQ.includes('najnowsze') || lowerQ.includes('ostatnie')) {
  result.filters.date_range = { start: "6 months ago" }
  result.top_k = 10
}

// ✅ Mapuje słowa kluczowe na tagi
'ai' → ['ai', 'sztuczna inteligencja', 'llm', 'agent']

// ✅ Wykrywa intencje sekcji
'checklist' → section_type: ['checklist'], top_k: 5
```

**Dynamiczny top_k:**
- Proste pytania: 5
- Złożone/nowe trendy: 10
- Domyślnie: 7 ✅

### 3. Formatowanie Kontekstu (9/10)
**Node "Format RAG Context" świetnie strukturyzuje dane:**
```javascript
context += `--- Wynik ${index + 1} (Score: ${score}%) ---`
context += `Tytuł: ${result.title}`
context += `URL: ${result.url}`
context += `Tagi: ${result.tags.join(', ')}`
```
✅ Obsługuje "brak wyników"
✅ Zwraca czytelny kontekst dla LLM

### 4. Timeout (10/10)
```json
"timeout": 60000  // 60s ✅
```
**Świetnie!** Zgodnie z wymaganiami (RAG może być wolny).

---

## ⚠️ PROBLEMY I BRAKI

### 🔴 KRYTYCZNE

#### 1. **BRAK AUTORYZACJI DO HUGGING FACE API**
```json
"url": "https://mobby-rag-search-api.hf.space/search",
"sendBody": true,
"jsonBody": "={{ $json.output }}"
```

**Problem:** Brakuje headerów z tokenem!

**Fix potrzebny:**
```json
"options": {
  "headerParametersJson": {
    "Authorization": "Bearer {{$env.HF_API_TOKEN}}",
    "Content-Type": "application/json"
  }
}
```

#### 2. **Niepoprawny format body dla RAG API**
Workflow wysyła:
```json
{
  "query": "...",
  "top_k": 7,
  "filters": {...}
}
```

**ALE** API Hugging Face prawdopodobnie oczekuje flatter structure albo innego formatu.

**Należy sprawdzić dokumentację HF Space** - czy:
- Filtry mają być nested czy flat?
- Czy `top_k` czy `limit`?

#### 3. **Brak error handlingu dla HTTP Request**
Co jeśli:
- HF Space timeout (>60s)?
- RAG API zwróci 500 error?
- Network failure?

**Brakuje Error Output node** do obsługi błędów.

---

### 🟡 DO POPRAWY

#### 4. **Code Tool może nie działać poprawnie w n8n**
```javascript
const question = $fromAI('question', '...', 'string');
```

**Problem:** `$fromAI()` to specjalna funkcja n8n dla AI tools, ale:
- W Code Tool może nie mieć dostępu do kontekstu
- Lepiej przekazać question jako parametr

**Fix:**
Zmienić na **HTTP Request Tool** lub **Workflow Tool** zamiast Code Tool.

#### 5. **Brak mappingu dla wszystkich kategorii z Twojego systemu**
W Code Tool jest tylko:
```javascript
if (lowerQ.includes('produkt')) result.filters.categories = ['Produkt'];
if (lowerQ.includes('design')) result.filters.categories = ['Design'];
```

**Brakuje:** innych kategorii z Twojego WordPress (jeśli są).

#### 6. **Nie wykorzystuje Qdrant bezpośrednio**
Workflow używa HF Space jako proxy, ale w prompcie podałem:
- Qdrant URL
- Qdrant API Key

**Pytanie:** Czy HF Space faktycznie odpytuje Qdrant? Jeśli tak - OK. Jeśli nie - trzeba dodać bezpośrednie wywołanie Qdrant.

---

### 🟢 DROBNE ULEPSZENIA

#### 7. **Temperatura dla Analyze Agent**
```json
"temperature": 0.3  // ✅ OK dla analizy
```

Ale dla **Answer Generator**:
```json
"temperature": 0.7  // może być za wysoka dla faktów
```

**Rekomendacja:** Zmniejsz do **0.4-0.5** (więcej precyzji, mniej halucynacji).

#### 8. **Response format**
```json
{
  "question": "...",
  "answer": "...",
  "sources_count": 5,
  "has_results": true
}
```

**Fajnie, ale brakuje:**
- `sources: [...]` - lista tytułów i linków
- `filters_used: {...}` - jakie filtry agent zastosował (debugging)

---

## 🎯 REKOMENDACJE

### Priorytet 1 (Krytyczne - bez tego nie zadziała)
1. **Dodać autoryzację do HF API**
2. **Zweryfikować format body** dla RAG API (sprawdź HF Space docs)
3. **Dodać error handling** (Error Output + fallback response)

### Priorytet 2 (Ważne - ulepszy działanie)
4. **Przepisać Code Tool** na HTTP Request Tool lub Workflow Sub-flow
5. **Dodać więcej mappingów** kategorii i tagów
6. **Zmniejszyć temperature** Answer Generator (0.7 → 0.5)

### Priorytet 3 (Nice to have)
7. **Zwracać listę źródeł** w response
8. **Logować decyzje agenta** (filters_used, top_k)
9. **Dodać retry logic** dla HTTP (3 próby z exponential backoff)

---

## 🔧 POPRAWIONY FRAGMENT - HTTP Request Node

```json
{
  "parameters": {
    "method": "POST",
    "url": "https://mobby-rag-search-api.hf.space/search",
    "sendBody": true,
    "specifyBody": "json",
    "jsonBody": "={{ $json.output }}",
    "options": {
      "timeout": 60000,
      "redirect": {
        "redirect": {
          "followRedirects": true,
          "maxRedirects": 3
        }
      },
      "response": {
        "response": {
          "fullResponse": false,
          "neverError": true
        }
      }
    },
    "sendHeaders": true,
    "headerParameters": {
      "parameters": [
        {
          "name": "Authorization",
          "value": "={{ $env.HF_API_TOKEN }}"
        },
        {
          "name": "Content-Type",
          "value": "application/json"
        }
      ]
    }
  }
}
```

---

## 📝 WERDYKT KOŃCOWY

**Co działa:**
✅ Architektura 2-agentowa (analyze → search → generate)
✅ Inteligentne mapowanie intencji na filtry
✅ Formatowanie kontekstu dla LLM
✅ Timeout 60s
✅ Obsługa "brak wyników"

**Co wymaga naprawy:**
🔴 Brak autoryzacji HF API
🔴 Niepewny format body dla RAG API
🔴 Brak error handlingu
🟡 Code Tool może nie działać w runtime

**Następne kroki:**
1. Dodaj headers z tokenem HF
2. Przetestuj workflow z przykładowym pytaniem
3. Sprawdź logi - czy HF API odpowiada poprawnie?
4. Dodaj error handling
5. Zoptymalizuj temperature dla Answer Generator

---

## 💡 DODATKOWE PYTANIA

1. **Czy HF Space wymaga autentykacji?** (Bearer token?)
2. **Jaki dokładnie format body akceptuje HF endpoint?**
3. **Czy HF Space już odpytuje Qdrant?** (czy musimy to robić bezpośrednio?)
4. **Jakie inne kategorie są w Twoim WordPress?** (do rozszerzenia mappingu)

Po uzyskaniu odpowiedzi mogę przygotować **poprawioną wersję workflow** gotową do importu.
