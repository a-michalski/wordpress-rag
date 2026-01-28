# N8N Agentowy Workflow RAG - Prompt dla AI

## CEL
Wygeneruj workflow n8n z AI Agentem, który inteligentnie odpytuje system RAG (Qdrant + Hugging Face) i buduje kontekstowe odpowiedzi w języku polskim.

## ARCHITEKTURA SYSTEMU RAG

**Qdrant Cloud:**
- URL: `https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io`
- API Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0`
- Kolekcja: `wordpress_articles`
- Embeddingi: dense (nomic-ai 768D), ColBERT (96D), sparse BM25
- Search: 2-etapowy (dense recall → ColBERT reranking)

**Hugging Face API (wyszukiwanie):**
- Endpoint: `https://mobby-rag-search-api.hf.space/search`
- Method: POST
- Body: `{"query": "pytanie", "top_k": 5-10, "filters": {...}}`

**Dostępne filtry RAG:**
- `tags`: Lista tagów (OR), np. ["AI", "product management"]
- `categories`: Lista kategorii (OR), np. ["Produkt", "Design"]
- `section_type`: Typ sekcji (OR): "tldr", "checklist", "key_insight", "content"
- `date_range`: {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}

**Zwracana struktura (SearchResult):**
```json
{
  "title": "Tytuł artykułu",
  "text": "Fragment tekstu",
  "score": 0.95,
  "url": "link",
  "section_type": "content",
  "tags": ["AI", "..."],
  "categories": ["Produkt"],
  "publication_date": "2025-01-15"
}
```

## WYMAGANY WORKFLOW N8N

**Node'y:**
1. **Webhook** (POST `/rag-agent`) - przyjmuje `{"question": "pytanie użytkownika"}`
2. **AI Agent Node** - analizuje pytanie i decyduje:
   - Czy użyć filtrów? Jakich?
   - Ile wyników pobrać (top_k: 5-10)?
   - Jaką strategię wyszukiwania?
3. **HTTP Request: RAG Search** - wywołuje HF API z parametrami od agenta
4. **Code/Function Node** - przetwarza wyniki RAG do czytelnego kontekstu
5. **AI Agent/LLM Node** - generuje odpowiedź w oparciu o:
   - Oryginalne pytanie
   - Kontekst z RAG
   - Metadata (źródła, daty, score)
6. **Respond to Webhook** - zwraca odpowiedź

## LOGIKA AGENTA

**Agent AI powinien:**
- Analizować intencję pytania (np. "najnowsze trendy" → filtr date_range)
- Wykrywać tematy (np. "AI", "product management") → filtr tags
- Rozpoznawać potrzebę konkretów → filtr section_type="checklist"/"tldr"
- Dostosowywać top_k (proste pytania: 5, złożone: 10)
- Budować odpowiedź cytując źródła z metadata

**Przykładowe decyzje:**
- "Jakie są najnowsze trendy w AI?" → date_range: {"start": "2024-01-01"}, tags: ["AI"], top_k: 10
- "Pokaż checklist dla product management" → section_type: ["checklist"], tags: ["product management"], top_k: 5
- "Jak używać agentów AI?" → tags: ["AI"], section_type: ["content", "key_insight"], top_k: 7

## PROMPT DLA LLM (w workflow)

```
Użytkownik zapytał: {{$node["Webhook"].json["body"]["question"]}}

Znaleziono następujący kontekst z bazy RAG:
{{kontekst_z_wyników}}

Twoim zadaniem:
1. Odpowiedz zwięźle w języku polskim
2. Cytuj źródła (tytuły artykułów, linki)
3. Uwzględnij score i daty publikacji
4. Jeśli brak wyników, zasugeruj przeformułowanie pytania

Odpowiedź:
```

## FORMAT OUTPUTU

Wygeneruj kompletny zawierający:
- Wszystkie node'y z prawidłowymi connections
- Skonfigurowane HTTP requesty z headers/auth
- AI Agent z tools/funkcjami do decyzji o filtrach
- Code node do formatowania kontekstu
- LLM node z promptem systemowym
- Error handling

**Kluczowe wymagania:**
- Odpowiedzi w języku polskim
- Timeout dla HTTP: min 60s (RAG może być wolny)
- Logowanie decyzji agenta (opcjonalnie)
- Obsługa przypadku "brak wyników"

Wygeneruj teraz workflow.
