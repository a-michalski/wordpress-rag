# 🚀 Deployment na Hetzner CX23

**Serwer:** CX23 (2 vCPU, 4GB RAM, x86) - €3.68/m
**Stack:** Ubuntu 24.04 LTS + Docker + FastAPI + ColBERT

---

## 📋 KROK 1: Zamów serwer Hetzner

1. Zaloguj się na https://console.hetzner.cloud
2. **Create Server**
3. **Location:** Wybierz najbliższy (np. Falkenstein, Germany)
4. **Image:** Ubuntu 24.04
5. **Type:** CX23 (2 vCPU, 4GB RAM)
6. **Networking:**
   - IPv4 ✅
   - IPv6 ✅
7. **SSH Key:** Dodaj swój klucz publiczny
8. **Name:** rag-search-api
9. **Create & Buy now**

**Dostaniesz:**
- IP adres serwera (np. 123.45.67.89)
- Root access przez SSH

---

## 📋 KROK 2: Pierwsze logowanie i update

```bash
# Zaloguj się do serwera
ssh root@123.45.67.89

# Update system
apt update && apt upgrade -y

# Install podstawowe narzędzia
apt install -y curl git vim htop
```

---

## 📋 KROK 3: Zainstaluj Docker

```bash
# Usuń stare wersje Dockera (jeśli były)
apt remove -y docker docker-engine docker.io containerd runc

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install -y docker-compose-plugin

# Sprawdź wersję
docker --version
docker compose version

# Enable Docker autostart
systemctl enable docker
systemctl start docker
```

---

## 📋 KROK 4: Sklonuj repozytorium

```bash
# Utwórz katalog dla aplikacji
mkdir -p /opt/rag-api
cd /opt/rag-api

# Opcja A: Jeśli repo jest na GitHubie
git clone https://github.com/TWOJ_USERNAME/RAG.git .

# Opcja B: Jeśli repo jest tylko lokalnie, skopiuj pliki
# (na lokalnym Mac):
# rsync -avz -e ssh /Users/adammichalski/Code/RAG/ root@123.45.67.89:/opt/rag-api/
```

**Alternatywa - ręczne kopiowanie:**
```bash
# Na serwerze utwórz strukturę
mkdir -p /opt/rag-api

# Na lokalnym Mac, z folderu RAG:
scp -r . root@123.45.67.89:/opt/rag-api/
```

---

## 📋 KROK 5: Konfiguracja środowiska

```bash
cd /opt/rag-api/deployment

# Skopiuj przykładowy plik .env
cp .env.example .env

# Edytuj .env i wstaw credentials
nano .env
```

**Zawartość `.env`:**
```bash
QDRANT_URL=https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io
QDRANT_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.PwJ_SxzrCUVng_lvSv-wycleWxPg2YYO4OJ6UMJ5fT0
```

Zapisz: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## 📋 KROK 6: Edytuj config.py (włącz grupowanie!)

```bash
cd /opt/rag-api
nano config.py
```

**Zmień te linie:**
```python
# Linia 40-42
ENABLE_GROUPING = True          # Zmień False → True
GROUP_BY_FIELD = "document_id"  # Zmień "post_id" → "document_id"
GROUP_SIZE = 1                  # max 1 chunk per article
```

**Dodaj brakujące parametry (na końcu pliku):**
```python
# Vector configuration (dla qdrant_setup.py)
DENSE_VECTOR_SIZE = 768
DENSE_DISTANCE_METRIC = "Cosine"
COLBERT_VECTOR_SIZE = 96
COLBERT_DISTANCE_METRIC = "Cosine"

# Memory optimization
ENABLE_BINARY_QUANTIZATION = True
DENSE_VECTORS_ON_DISK = True
COLBERT_VECTORS_ON_DISK = False
QUANTIZATION_ALWAYS_RAM = True
```

Zapisz i wyjdź.

---

## 📋 KROK 7: Build i uruchom Docker

```bash
cd /opt/rag-api/deployment

# Build Docker image (może zająć 5-10 minut)
docker compose build

# Uruchom w tle
docker compose up -d

# Sprawdź logi
docker compose logs -f
```

**Oczekiwany output:**
```
rag-search-api  | INFO:     Started server process
rag-search-api  | INFO:     Uvicorn running on http://0.0.0.0:8000
rag-search-api  | Connected to Qdrant Cloud: https://79a7ee05...
```

Wciśnij `Ctrl+C` żeby wyjść z logów (kontener dalej działa).

---

## 📋 KROK 8: Test API

```bash
# Test health check
curl http://localhost:8000/health

# Test search (z serwera)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Jak używać agentów AI?",
    "top_k": 5
  }'
```

**Oczekiwany output:**
```json
{
  "query": "Jak używać agentów AI?",
  "results": [
    {
      "title": "...",
      "text": "...",
      "score": 0.87,
      "url": "..."
    }
  ],
  "total": 5,
  "config": {
    "two_stage_search": true,
    "colbert_reranking": true
  }
}
```

---

## 📋 KROK 9: Konfiguracja firewall i domena (opcjonalnie)

### **Firewall (zalecane):**
```bash
# Install UFW
apt install -y ufw

# Zezwól SSH (WAŻNE - nie zablokuj się!)
ufw allow 22/tcp

# Zezwól API (port 8000)
ufw allow 8000/tcp

# Włącz firewall
ufw enable

# Sprawdź status
ufw status
```

### **Domena (opcjonalnie):**
Jeśli masz domenę (np. `api.twojblog.pl`):

1. **Dodaj A record** w DNS:
   ```
   api.twojblog.pl → 123.45.67.89
   ```

2. **Install Nginx reverse proxy:**
   ```bash
   apt install -y nginx certbot python3-certbot-nginx

   # Konfiguracja Nginx
   nano /etc/nginx/sites-available/rag-api
   ```

   **Zawartość:**
   ```nginx
   server {
       listen 80;
       server_name api.twojblog.pl;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

   ```bash
   # Aktywuj
   ln -s /etc/nginx/sites-available/rag-api /etc/nginx/sites-enabled/
   nginx -t
   systemctl reload nginx

   # SSL (HTTPS) przez Let's Encrypt
   certbot --nginx -d api.twojblog.pl
   ```

---

## 📋 KROK 10: Zmień n8n workflow

**W n8n, node "HTTP: Fireworks Nomic Embed":**

**PRZED (Fireworks):**
```
URL: https://api.fireworks.ai/inference/v1/embeddings
```

**PO (Twój serwer):**
```
URL: http://123.45.67.89:8000/search
Method: POST
Body:
{
  "query": "{{ $json.output.query }}",
  "top_k": {{ $json.output.top_k }}
}
```

**Usuń node:**
- ❌ "HTTP: Fireworks Nomic Embed" (nie potrzebny)
- ❌ "Code: Prepare Qdrant Query1" (nie potrzebny)
- ❌ "HTTP: Qdrant Search1" (nie potrzebny)

**Nowy flow:**
```
Webhook → AI Agent (analyze) → HTTP (Twój API /search) → Format → AI Agent (answer)
```

---

## 🔧 Zarządzanie serwerem

### **Restart API:**
```bash
docker compose restart
```

### **Stop API:**
```bash
docker compose down
```

### **Aktualizacja kodu:**
```bash
cd /opt/rag-api
git pull  # lub scp nowych plików
docker compose down
docker compose build
docker compose up -d
```

### **Logi:**
```bash
# Real-time logs
docker compose logs -f

# Last 100 lines
docker compose logs --tail=100
```

### **Monitoring zasobów:**
```bash
# CPU, RAM, Disk
htop

# Docker stats
docker stats
```

---

## 📊 Co dostaniesz?

**Endpoint:** `http://123.45.67.89:8000`

**Features:**
- ✅ Dense vector search (nomic-embed-text-v1.5)
- ✅ ColBERT reranking (MaxSim scoring)
- ✅ Sparse BM25 vectors
- ✅ Grupowanie po document_id (max 1 chunk/article)
- ✅ Filtry (tags, categories, dates, section_type)
- ✅ Swagger docs na `/docs`

**Koszty:**
- Hetzner CX23: €3.68/m
- Qdrant Cloud: FREE (1GB)
- **Total: €3.68/m** (~16 PLN)

---

## 🐛 Troubleshooting

### Problem: Build Docker trwa wieczność
**Przyczyna:** Pobieranie modeli embedding (768MB + 250MB)

**Fix:** Zaczekaj, to tylko pierwszy raz. Następne buildy będą szybkie (cache).

### Problem: Container crashuje (OOM - Out of Memory)
**Przyczyna:** Za dużo requestów naraz, przekroczono 4GB RAM

**Fix 1:** Restart container:
```bash
docker compose restart
```

**Fix 2:** Zmniejsz workers w Dockerfile (już ustawiony na 1):
```dockerfile
CMD ["uvicorn", "deployment.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

### Problem: "Module not found: search"
**Przyczyna:** Złe ścieżki w app.py

**Fix:** Sprawdź czy wszystkie pliki są w `/opt/rag-api/`:
```bash
ls -la /opt/rag-api/
# Powinny być: search.py, embeddings.py, config.py, qdrant_setup.py
```

### Problem: Nie mogę połączyć się z API (timeout)
**Fix:**
```bash
# Sprawdź czy container działa
docker ps

# Sprawdź firewall
ufw status

# Sprawdź logi
docker compose logs
```

---

## ✅ Checklist przed produkcją

- [ ] Serwer Hetzner utworzony i działa
- [ ] Docker zainstalowany
- [ ] Kod skopiowany do `/opt/rag-api/`
- [ ] `.env` skonfigurowany z Qdrant credentials
- [ ] `config.py` - ENABLE_GROUPING = True
- [ ] Docker container uruchomiony (`docker compose up -d`)
- [ ] `/health` endpoint zwraca 200 OK
- [ ] `/search` zwraca wyniki z ColBERT reranking
- [ ] n8n workflow zaktualizowany (nowy endpoint)
- [ ] Firewall skonfigurowany (UFW)
- [ ] (Opcjonalnie) Domena i SSL skonfigurowane

**Gotowe!** 🎉
