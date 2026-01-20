# n8n workflow: RAG Search -> LLM (Webhook)

This folder contains an importable n8n workflow JSON that implements a minimal RAG flow:

- Webhook trigger (`/webhook/rag-search`) — receive POSTs with JSON `{ "question": "..." }`
- HTTP Request `Call RAG API` — queries the deployed RAG search API (`/search`). Replace the placeholder token.
- `Build Prompt` — formats a prompt combining the user question and RAG results.
- HTTP Request `Call LLM` — sends prompt to an LLM (OpenAI-compatible endpoint). Replace placeholder API key.
- `Return Response` — responds to the incoming webhook with the LLM answer.

Quick setup

1. Import `rag_search_workflow.json` into n8n (Workflows → Import).
2. Edit the `Call RAG API` node: replace `REPLACE_WITH_RAG_TOKEN` with your RAG API token (or set a credential and update the node).
3. Edit the `Call LLM` node: replace `REPLACE_WITH_OPENAI_KEY` with your OpenAI/OpenRouter key.
4. Activate the workflow.

Test with curl

```bash
curl -X POST https://<your-n8n-webhook-host>/webhook/rag-search \
  -H "Content-Type: application/json" \
  -d '{"question":"Jak zainstalować Kubernetes na Macu?"}'
```

Notes & recommendations

- Replace placeholders with credentials rather than leaving secrets in the workflow file.
- Set HTTP Request timeouts to 60s and retries (2) on the `Call RAG API` and `Call LLM` nodes.
- Limit `top_k` to a value that keeps prompt size within your LLM token budget (e.g., 3-8).
- Monitor execution times in n8n and add logging or a metric sink if needed.

Import & Setup (quick)

- Import the workflow: In n8n, go to Workflows → Import and choose `rag_search_workflow.json`.
- Replace placeholders: open the `Call RAG API` node and set the `Authorization` header to `Bearer <RAG_API_TOKEN>` (use n8n Credentials / Environment Variables rather than storing secrets inline).
- Configure LLM node: open `Call LLM` and set `Authorization` header to `Bearer <OPENAI_OR_OPENROUTER_KEY>` or use n8n Credentials.
- Activate: save and activate the workflow. The webhook path is `/webhook/rag-search` (your n8n host base + that path).

Test request

```bash
curl -X POST https://<your-n8n-host>/webhook/rag-search \
  -H "Content-Type: application/json" \
  -d '{"question":"Jak zainstalować Kubernetes na Macu?"}'
```

Deployment & Timeout Recommendations

- HTTP timeouts: set `Timeout` to 60000 ms (60s) on `Call RAG API` and `Call LLM` nodes. Increase if your LLM or RAG calls are slow.
- Retries: enable 2 retries with exponential backoff for intermittent network errors.
- Top-k: prefer `top_k` = 3–5 for concise prompts; increase only if you trim passages to fit tokens.
- Token/Prompt budget: target LLM prompt + expected response ≤ model token limit (for `gpt-4o-mini` aim for ≤ 8k tokens). Use `max_tokens` (e.g., 500) for responses.
- Safety: never commit secrets to git. Use n8n Credentials, Environment Variables, or a Vault.
- Monitoring: enable execution logging in n8n, add a webhook to report failures, or push metrics to Prometheus/Datadog.
- Performance: keep RAG responses short (select `text` + `url`), and consider server-side reranking if you need higher accuracy.

If you want, I can:

- swap placeholders for n8n Credential references in the JSON,
- produce a minimal example that uses only HTTP Request + external LLM provider, or
- add a small test harness script that posts sample questions to your n8n webhook.

