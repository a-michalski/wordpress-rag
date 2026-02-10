# Integracja n8n z RAG API na Hetzner

## Status deploymentu

✅ **API działa:** http://89.167.41.22:8000
- Health endpoint: `/health`
- Search endpoint: `/search` (POST)
- Docs (Swagger): `/docs`
- 7725 dokumentów w Qdrant Cloud
- ColBERT reranking aktywny
- **Grouping: WYŁĄCZONY** (brak payload index w Qdrant Cloud)

## Szybki test API

### Health check
```bash
curl http://89.167.41.22:8000/health
```

Odpowiedź:
```json
{
  "status": "healthy",
  "collection": "wordpress_articles",
  "points": 7725,
  "vectors": ["colbert", "dense"],
  "models": {
    "dense": "nomic-ai/nomic-embed-text-v1.5",
    "colbert": "answerdotai/answerai-colbert-small-v1",
    "sparse": "Qdrant/bm25"
  }
}
```

### Test search
```bash
curl -X POST "http://89.167.41.22:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wordpress performance",
    "top_k": 3
  }'
```

## Konfiguracja n8n workflow

### Zastąp Fireworks AI node → HTTP Request node

**Stare workflow:**
```
Trigger → Fireworks AI (embeddings) → Qdrant Search → OpenRouter → Response
```

**Nowe workflow:**
```
Trigger → HTTP Request (Twój API) → OpenRouter → Response
```

### Node: HTTP Request do RAG API

**Konfiguracja:**
- **Method:** POST
- **URL:** `http://89.167.41.22:8000/search`
- **Authentication:** None (póki co)
- **Body Content Type:** JSON
- **Specify Body:** Using Fields Below

**Body (JSON):**
```json
{
  "query": "{{ $json.query }}",
  "top_k": 5
}
```

**Opcjonalne parametry:**
```json
{
  "query": "{{ $json.query }}",
  "top_k": 5,
  "include_full_article": true,
  "filters": {
    "tags": ["AI", "Design"],
    "categories": ["Technologia"],
    "section_type": ["content", "key_insight"]
  }
}
```

**Parametr `include_full_article`:**
- `false` (default): Zwraca tylko dopasowany chunk (~512-1024 tokeny)
- `true`: Zwraca chunk + pełny artykuł (wszystkie chunki złożone w całość)
- Przydatne gdy LLM potrzebuje pełnego kontekstu artykułu
- Jeden request zamiast wielu - szybsze i bardziej efektywne

### Przetwarzanie odpowiedzi

API zwraca:
```json
{
  "query": "wordpress performance",
  "results": [
    {
      "chunk_id": "972_5",
      "document_id": "972",
      "title": "Tytuł artykułu",
      "url": "https://...",
      "text": "Treść chunka...",
      "score": 5.394,
      "section_type": "content",
      "author": "michalski.adam",
      "publication_date": "2025-05-08T19:51:56",
      "categories": ["AI", "Encrypted notes"],
      "tags": ["AI w Designie", "WordPress"],
      "full_article": "Pełny artykuł (wszystkie chunki)..."  // tylko gdy include_full_article=true
    }
  ],
  "total": 3,
  "config": {
    "two_stage_search": true,
    "colbert_reranking": true,
    "recall_limit": 100,
    "grouping": true
  }
}
```

### Formatowanie dla OpenRouter

**Node: Set** - przygotowanie kontekstu

**Opcja A: Tylko dopasowane chunki (krótszy kontekst)**
```javascript
// Pobierz wyniki z API
const results = $json.results;

// Sformatuj jako kontekst dla LLM
const context = results.map((r, i) =>
  `[${i+1}] ${r.title}\n${r.text}\nŹródło: ${r.url}\n`
).join('\n---\n');

return {
  query: $json.query,
  context: context,
  sources: results.map(r => ({
    title: r.title,
    url: r.url,
    score: r.score
  }))
};
```

**Opcja B: Pełne artykuły (gdy include_full_article=true)**
```javascript
// Pobierz wyniki z API
const results = $json.results;

// Użyj pełnych artykułów zamiast chunków
const context = results.map((r, i) =>
  `[${i+1}] ${r.title}\n${r.full_article || r.text}\nŹródło: ${r.url}\n`
).join('\n---\n');

return {
  query: $json.query,
  context: context,
  sources: results.map(r => ({
    title: r.title,
    url: r.url,
    score: r.score
  }))
};
```

**Node: OpenRouter** - generowanie odpowiedzi

System prompt:
```
Jesteś asystentem AI specjalizującym się w tematach UX/UI design, AI i technologii.
Odpowiadaj na podstawie dostarczonych źródeł. Zawsze cytuj źródła używając numerów [1], [2] etc.
```

User message:
```
Kontekst ze źródeł:
{{ $json.context }}

Pytanie użytkownika:
{{ $json.query }}

Odpowiedz na pytanie wykorzystując informacje z kontekstu. Cytuj źródła.
```

## Przykładowy pełny workflow n8n

```json
{
  "nodes": [
    {
      "name": "Webhook",
      "type": "n8n-nodes-base.webhook",
      "parameters": {
        "path": "rag-search",
        "httpMethod": "POST"
      }
    },
    {
      "name": "RAG Search",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "http://89.167.41.22:8000/search",
        "jsonParameters": true,
        "bodyParametersJson": "={\"query\": \"{{ $json.body.query }}\", \"top_k\": 5}"
      }
    },
    {
      "name": "Format Context",
      "type": "n8n-nodes-base.set",
      "parameters": {
        "mode": "manual",
        "values": {
          "string": [
            {
              "name": "context",
              "value": "={{$json.results.map((r,i)=>`[${i+1}] ${r.title}\\n${r.text}\\nŹródło: ${r.url}`).join('\\n---\\n')}}"
            },
            {
              "name": "query",
              "value": "={{$json.query}}"
            }
          ]
        }
      }
    },
    {
      "name": "OpenRouter",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "method": "POST",
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "sendHeaders": true,
        "headerParameters": {
          "parameters": [
            {
              "name": "HTTP-Referer",
              "value": "https://uxairforce.com"
            }
          ]
        },
        "jsonParameters": true,
        "bodyParametersJson": "={\"model\": \"anthropic/claude-3.5-sonnet\", \"messages\": [{\"role\": \"system\", \"content\": \"Jesteś asystentem AI. Odpowiadaj na podstawie źródeł.\"}, {\"role\": \"user\", \"content\": `Kontekst:\\n${$json.context}\\n\\nPytanie: ${$json.query}`}]}"
      }
    },
    {
      "name": "Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{$json}}"
      }
    }
  ]
}
```

## Dostępne filtry

### Filtry po tagach
```json
{
  "query": "AI w designie",
  "top_k": 5,
  "filters": {
    "tags": ["AI w Designie", "Claude Code"]
  }
}
```

### Filtry po kategoriach
```json
{
  "query": "design systems",
  "top_k": 5,
  "filters": {
    "categories": ["Design", "Technologia"]
  }
}
```

### Filtry po typie sekcji
```json
{
  "query": "best practices",
  "top_k": 5,
  "filters": {
    "section_type": ["key_insight", "tldr"]
  }
}
```

### Filtry po dacie
```json
{
  "query": "nowości AI",
  "top_k": 5,
  "filters": {
    "date_range": {
      "start": "2024-01-01",
      "end": "2024-12-31"
    }
  }
}
```

### Kombinacja filtrów
```json
{
  "query": "AI tools",
  "top_k": 5,
  "filters": {
    "tags": ["AI w Designie"],
    "categories": ["Technologia"],
    "section_type": ["content"],
    "date_range": {
      "start": "2024-06-01"
    }
  }
}
```

## Monitoring i debugowanie

### Sprawdź status API
```bash
curl http://89.167.41.22:8000/health
```

### Zobacz logi Docker
```bash
ssh rag "docker compose -f /opt/rag-api/deployment/docker-compose.yml logs --tail=100 rag-api"
```

### Restart API (jeśli potrzeba)
```bash
ssh rag "docker compose -f /opt/rag-api/deployment/docker-compose.yml restart"
```

### Pełny restart (rebuild)
```bash
ssh rag "cd /opt/rag-api/deployment && docker compose down && docker compose up -d"
```

## Różnice między starym a nowym workflow

| Aspekt | Stary (Fireworks) | Nowy (Hetzner API) |
|--------|-------------------|-------------------|
| Embedding | Fireworks AI API | FastEmbed lokalnie |
| Reranking | ❌ Brak | ✅ ColBERT MaxSim |
| Koszt | ~$0.0001/query | €3.68/miesiąc (flat) |
| Latency | 200-500ms | 100-300ms (estimate) |
| Kontrola | Zewnętrzny service | Twój serwer |
| Grouping | ❌ Ręczne | ⚠️ Wymaga indexu |
| Skalowanie | Auto (Fireworks) | Manualnie (upgrade CPU) |

## Następne kroki

1. **Teraz:** Przetestuj search endpoint z n8n HTTP Request node
2. **Opcjonalnie:** Dodaj payload index dla grouping w Qdrant Cloud
3. **W przyszłości:** Rozważ upgrade do qdrant-client 1.16.2 (zobacz UPGRADE_QDRANT.md)
4. **Security:** Dodaj API key authentication gdy będzie produkcja

## Kontakt z API

- **Server:** 89.167.41.22
- **Port:** 8000
- **SSH:** `ssh rag`
- **Swagger docs:** http://89.167.41.22:8000/docs
- **Health:** http://89.167.41.22:8000/health
- **Search:** http://89.167.41.22:8000/search (POST)

## Uwagi o wydajności

- Pierwsze zapytanie: wolniejsze (ładowanie modeli)
- Kolejne zapytania: szybkie (modele w cache)
- Timeout: 60s (można zwiększyć w docker-compose.yml)
- Concurrent requests: 1 worker (można zwiększyć w CMD)

## Troubleshooting

### Problem: Connection refused
**Rozwiązanie:** Sprawdź czy kontener działa: `ssh rag "docker ps"`

### Problem: 500 Internal Server Error
**Rozwiązanie:** Zobacz logi: `ssh rag "docker compose -f /opt/rag-api/deployment/docker-compose.yml logs --tail=50"`

### Problem: Wolne odpowiedzi
**Rozwiązanie:** Zmniejsz `top_k` lub `RECALL_LIMIT` w config.py

### Problem: Brak wyników
**Rozwiązanie:** Sprawdź filtry - mogą być zbyt restrykcyjne
