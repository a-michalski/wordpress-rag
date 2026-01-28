# N8N Workflow - Szybka naprawa OpenRouter

## ZADANIE
Popraw workflow dodając brakującą konfigurację OpenRouter i credentials.

## CO NAPRAWIĆ

### 1. OpenRouter nodes - DODAJ baseURL

**Nodes do zmiany:**
- "OpenRouter: Analyze Model"
- "OpenRouter: Answer Generator"

**W każdym dodaj:**
```json
"options": {
  "baseURL": "https://openrouter.ai/api/v1",
  "temperature": 0.3  // lub 0.5 dla Answer Generator
}
```

### 2. Credentials - ZMIEŃ z free credits na OPENROUTER_API_KEY

**W obu OpenRouter nodes zamień:**
```json
// BYŁO:
"credentials": {
  "openAiApi": {
    "id": "oUzECR7JM8Hc13Hm",
    "name": "n8n free OpenAI API credits"
  }
}

// MA BYĆ:
"credentials": {
  "openAiApi": "={{$env.OPENROUTER_API_KEY}}"
}
```

### 3. Opcjonalnie - usuń "1" z nazw node'ów

Zmień nazwy dla czytelności:
- "Webhook: RAG Question1" → "Webhook: RAG Question"
- "AI Agent: Analyze Question1" → "AI Agent: Analyze Question"
- (etc. dla wszystkich)

## WYNIK

Zwróć poprawiony JSON workflow gotowy do importu.

**Checklist:**
- [ ] baseURL w OpenRouter nodes
- [ ] Credentials z $env.OPENROUTER_API_KEY
- [ ] Nazwy bez "1" (opcjonalnie)
