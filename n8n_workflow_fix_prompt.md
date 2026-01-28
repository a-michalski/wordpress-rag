# N8N Workflow Fix - Prompt dla AI

## CEL
Popraw workflow "Polish AI Agent with RAG": usuń filtry (HF API ich nie obsługuje), dodaj OpenRouter, autoryzację, error handling.

## PROBLEMY
1. Brak auth HF API
2. HF API akceptuje TYLKO `{query, top_k}` - ignoruje `filters`
3. Brak error handling
4. Google Gemini → zamień na OpenRouter
5. Temperature 0.7 → 0.5
6. Response bez sources array

## ZMIANY

### 1. Code Tool: Build RAG Parameters - USUŃ FILTRY
```javascript
const question = $fromAI('question', 'User question', 'string');
const lowerQ = question.toLowerCase();
const result = { query: question, top_k: 10 };
if (lowerQ.includes('szczegół') || lowerQ.includes('jak')) result.top_k = 15;
else if (lowerQ.includes('przykład')) result.top_k = 12;
return JSON.stringify(result, null, 2);
```

### 2. HTTP Request: RAG Search - DODAJ AUTH
```json
"sendHeaders": true,
"headerParameters": {
  "parameters": [
    {"name": "Authorization", "value": "={{ $env.HF_API_TOKEN }}"},
    {"name": "Content-Type", "value": "application/json"}
  ]
},
"options": {"timeout": 60000, "response": {"neverError": true}}
```

### 3. Google Gemini → OpenRouter (oба node'y)
```json
{
  "type": "@n8n/n8n-nodes-langchain.lmChatOpenAi",
  "parameters": {
    "modelName": "anthropic/claude-3.5-sonnet",
    "options": {
      "baseURL": "https://openrouter.ai/api/v1",
      "temperature": 0.3  // dla Analyze, 0.5 dla Answer
    }
  },
  "credentials": {"openAiApi": {"apiKey": "={{ $env.OPENROUTER_API_KEY }}"}}
}
```
Modele: `anthropic/claude-3.5-sonnet`, `openai/gpt-4-turbo`, `google/gemini-pro-1.5`

### 4. Nowy node: Check API Errors (po HTTP Request)
```javascript
const r = $input.item.json;
if (!r || r.error) return {json: {context: `Błąd RAG: ${r?.error}`, hasResults: false, resultCount: 0}};
if (!r.results || r.results.length === 0) return {json: {context: 'Brak wyników. Przeformułuj pytanie.', hasResults: false, resultCount: 0}};
return {json: r};
```
Połącz: HTTP Request → Check Errors → Format Context

### 5. Respond to Webhook - dodaj sources array
```json
"responseBody": "={{ {
  \"question\": $('Code: Format RAG Context').item.json.originalQuestion,
  \"answer\": $json.output,
  \"sources\": $('Code: Format RAG Context').item.json.results.map(r => ({\"title\": r.title, \"url\": r.url, \"score\": r.score})),
  \"sources_count\": $('Code: Format RAG Context').item.json.resultCount
} }}"
```

### 6. Structured Output Parser - usuń filters
```json
"inputSchema": "{\"type\": \"object\", \"properties\": {\"query\": {\"type\": \"string\"}, \"top_k\": {\"type\": \"number\"}}, \"required\": [\"query\", \"top_k\"]}"
```

## ENV VARIABLES (n8n Settings)
- `HF_API_TOKEN` = hf_xxx
- `OPENROUTER_API_KEY` = sk-or-xxx

## CHECKLIST
- [ ] Usunięte filtry Code Tool
- [ ] Auth headers HTTP Request
- [ ] Gemini → OpenRouter (2x)
- [ ] Error handling node
- [ ] Sources array w response
- [ ] Schema bez filters
- [ ] Temp 0.5 Answer Gen

Wygeneruj poprawiony JSON workflow.
