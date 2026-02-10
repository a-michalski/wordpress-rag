# 🚀 RAG API Deployment

**Serwer:** Hetzner CX23 (2 vCPU, 4GB RAM, €3.68/m)
**Stack:** FastAPI + ColBERT Reranking + Qdrant Cloud

---

## 📁 Pliki w tym folderze

```
deployment/
├── SETUP.md              ← GŁÓWNA INSTRUKCJA (czytaj to!)
├── app.py                ← FastAPI z ColBERT reranking
├── Dockerfile            ← Multi-stage build
├── docker-compose.yml    ← Orchestration
├── deploy.sh             ← Automated deployment script
├── .env.example          ← Template dla credentials
└── README.md             ← Ten plik
```

---

## ⚡ Quick Start (3 komendy)

### **Na lokalnym Mac:**
```bash
# 1. Skopiuj pliki na serwer
cd /Users/adammichalski/Code/RAG
scp -r . root@123.45.67.89:/opt/rag-api/

# 2. Utwórz .env na serwerze
ssh root@123.45.67.89
cd /opt/rag-api/deployment
cp .env.example .env
nano .env  # wstaw credentials
```

### **Na serwerze:**
```bash
# 3. Uruchom automated deployment
cd /opt/rag-api/deployment
chmod +x deploy.sh
sudo ./deploy.sh
```

**Done!** API działa na `http://IP:8000`

---

## 📖 Dokumentacja

### **Szczegółowa instrukcja:**
👉 **[SETUP.md](./SETUP.md)** - Krok po kroku deployment

### **API Endpoints:**

#### `GET /`
Status API + dostępne features

#### `GET /health`
Health check + statystyki Qdrant

#### `GET /stats`
Szczegółowe statystyki kolekcji

#### `POST /search`
**Request:**
```json
{
  "query": "Jak używać agentów AI?",
  "top_k": 10,
  "filters": {
    "tags": ["AI"],
    "categories": ["Technologia"],
    "section_type": ["content", "key_insight"]
  }
}
```

**Response:**
```json
{
  "query": "Jak używać agentów AI?",
  "results": [
    {
      "title": "...",
      "url": "...",
      "text": "...",
      "score": 0.87,
      "section_type": "content",
      "tags": ["AI", "development"]
    }
  ],
  "total": 10,
  "config": {
    "two_stage_search": true,
    "colbert_reranking": true,
    "recall_limit": 100,
    "grouping": true
  }
}
```

#### `GET /docs`
Swagger UI (interactive API docs)

---

## 🎯 Features

### ✅ Co dostaniesz:
- **Dense vector search** - nomic-embed-text-v1.5 (768 dim)
- **ColBERT reranking** - MaxSim scoring dla precision
- **Sparse BM25** - keyword matching
- **Two-stage pipeline:**
  1. Dense recall (top 100 candidates)
  2. ColBERT reranking (top K results)
- **Grupowanie** - max 1 chunk per article (różnorodność)
- **Filtry** - tags, categories, dates, section_type
- **Swagger docs** - `/docs` endpoint
- **Health checks** - `/health` monitoring

### ❌ Co już NIE potrzebujesz:
- Fireworks AI API (embeddingi robione lokalnie)
- Zewnętrzne API calls (wszystko na Twoim serwerze)
- n8n nodes do Qdrant (API robi to za Ciebie)

---

## 🔧 Zarządzanie

### **Restart:**
```bash
docker compose restart
```

### **Logi:**
```bash
docker compose logs -f
```

### **Stop:**
```bash
docker compose down
```

### **Update kodu:**
```bash
git pull  # lub scp nowych plików
docker compose down && docker compose build && docker compose up -d
```

### **Monitoring:**
```bash
htop              # CPU, RAM
docker stats      # Container stats
```

---

## 🔗 Integracja z n8n

**Stary flow (z Fireworks):**
```
Webhook → Analyze → Fireworks API → Qdrant API → Format → LLM
```

**Nowy flow (z Twoim API):**
```
Webhook → Analyze → Twój API (/search) → Format → LLM
```

**Zmiana w n8n:**
1. Usuń nodes: Fireworks, Prepare Qdrant Query, Qdrant Search
2. Dodaj jeden HTTP node:
   - URL: `http://123.45.67.89:8000/search`
   - Method: POST
   - Body:
     ```json
     {
       "query": "{{ $json.output.query }}",
       "top_k": {{ $json.output.top_k || 10 }}
     }
     ```

**Response będzie gotowy do użycia w AI Agent (Generate Answer).**

---

## 💰 Koszty

| Serwis | Koszt |
|--------|-------|
| Hetzner CX23 | €3.68/m (~16 PLN) |
| Qdrant Cloud | FREE (1GB) |
| n8n (Oracle) | FREE |
| **Total** | **€3.68/m** |

---

## 🆘 Support

**Problem z deployment?**
1. Sprawdź `deployment/SETUP.md` - sekcja Troubleshooting
2. Sprawdź logi: `docker compose logs`
3. Test health: `curl http://localhost:8000/health`

**Checklist:**
- [ ] Docker zainstalowany (`docker --version`)
- [ ] `.env` z credentials Qdrant
- [ ] `config.py` - ENABLE_GROUPING = True
- [ ] Container działa (`docker ps`)
- [ ] Firewall zezwala port 8000 (`ufw status`)

---

## 📊 Porównanie: Przed vs Po

| Feature | Przed (n8n + Fireworks) | Po (Hetzner + FastAPI) |
|---------|-------------------------|------------------------|
| Dense search | ✅ (przez Fireworks) | ✅ (lokalnie) |
| ColBERT reranking | ❌ | ✅ |
| Sparse BM25 | ❌ | ✅ |
| Grupowanie | ❌ | ✅ |
| Filtry | ❌ | ✅ |
| Latencja | ~1-2s | ~500-800ms |
| Koszt | €0 | €3.68/m |
| Kontrola | ❌ | ✅ |
| Zimny start | ✅ (problem) | ❌ |

**Wniosek:** Za €3.68/m dostajesz pełną kontrolę + lepszą jakość wyników.

---

✅ **Gotowe do deployment? Czytaj [SETUP.md](./SETUP.md)**
