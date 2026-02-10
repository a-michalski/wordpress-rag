# Upgrade Guide: Qdrant Client 1.11.3 → 1.16.2

## Dlaczego warto zaktualizować?

Obecna wersja **1.11.3** działa stabilnie, ale **1.16.2** oferuje:
- Najnowsze funkcje i poprawki bezpieczeństwa
- Lepsza wydajność
- Długoterminowe wsparcie (long-term support)
- Nowe API zgodne z najnowszą dokumentacją

## Zmiany w API (Breaking Changes)

### 1. Metoda search() → query_points()

**Przed (1.11.3):**
```python
candidates = self.client.search(
    collection_name=self.collection_name,
    query_vector=("dense", query_embedding.tolist()),
    limit=limit,
    query_filter=qdrant_filter,
    with_payload=True,
)
```

**Po (1.16.2):**
```python
from qdrant_client.models import NamedVector

candidates = self.client.query_points(
    collection_name=self.collection_name,
    query=query_embedding.tolist(),  # Bez ("dense", ...)
    using="dense",  # Określamy nazwany wektor osobno
    limit=limit,
    query_filter=qdrant_filter,
    with_payload=True,
).points
```

### 2. Metoda search_groups() → query_points_groups()

**Przed (1.11.3):**
```python
results = self.client.search_groups(
    collection_name=self.collection_name,
    query_vector=("dense", query_embedding.tolist()),
    group_by=config.GROUP_BY_FIELD,
    group_size=config.GROUP_SIZE,
    limit=limit,
    query_filter=qdrant_filter,
    with_payload=True,
)

# Flatten groups to points
candidates = []
for group in results.groups:
    candidates.extend(group.hits)
```

**Po (1.16.2):**
```python
results = self.client.query_points_groups(
    collection_name=self.collection_name,
    query=query_embedding.tolist(),
    using="dense",
    group_by=config.GROUP_BY_FIELD,
    group_size=config.GROUP_SIZE,
    limit=limit,
    query_filter=qdrant_filter,
    with_payload=True,
)

# Flatten groups to points
candidates = []
for group in results.groups:
    candidates.extend(group.hits)
```

## Krok po kroku: Jak zaktualizować

### 1. Backup obecnego kodu

```bash
cd /Users/adammichalski/Code/RAG
git add .
git commit -m "Backup before Qdrant client upgrade to 1.16.2"
```

### 2. Zaktualizuj requirements.txt

**Plik:** `deployment/requirements.txt`

```diff
- qdrant-client==1.11.3
+ qdrant-client==1.16.2
```

### 3. Zaktualizuj search.py

**Plik:** `search.py`

**Zmiana 1: Import (linia ~11)**
```python
# Dodaj nowy import
from qdrant_client.models import NamedVector  # DODAJ TĘ LINIĘ
```

**Zmiana 2: Metoda _dense_recall() (linia ~137-164)**

Zamień cały blok:
```python
# STARY KOD (USUŃ):
if config.ENABLE_GROUPING:
    results = self.client.search_groups(
        collection_name=self.collection_name,
        query_vector=("dense", query_embedding.tolist()),
        group_by=config.GROUP_BY_FIELD,
        group_size=config.GROUP_SIZE,
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    candidates = []
    for group in results.groups:
        candidates.extend(group.hits)
else:
    candidates = self.client.search(
        collection_name=self.collection_name,
        query_vector=("dense", query_embedding.tolist()),
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )
```

Na:
```python
# NOWY KOD (WKLEJ):
if config.ENABLE_GROUPING:
    results = self.client.query_points_groups(
        collection_name=self.collection_name,
        query=query_embedding.tolist(),
        using="dense",
        group_by=config.GROUP_BY_FIELD,
        group_size=config.GROUP_SIZE,
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    candidates = []
    for group in results.groups:
        candidates.extend(group.hits)
else:
    result = self.client.query_points(
        collection_name=self.collection_name,
        query=query_embedding.tolist(),
        using="dense",
        limit=limit,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    candidates = result.points
```

### 4. Przetestuj lokalnie (opcjonalnie)

```bash
# Stwórz test środowisko
python -m venv test_env
source test_env/bin/activate
pip install -r deployment/requirements.txt

# Uruchom test search
python search.py
```

### 5. Deploy na serwer

```bash
# Skopiuj zaktualizowane pliki
scp deployment/requirements.txt rag:/opt/rag-api/deployment/
scp search.py rag:/opt/rag-api/

# SSH na serwer i rebuild
ssh rag "cd /opt/rag-api/deployment && docker compose down && docker compose build --no-cache"

# Uruchom
ssh rag "cd /opt/rag-api/deployment && docker compose up -d"

# Sprawdź logi
ssh rag "docker compose -f /opt/rag-api/deployment/docker-compose.yml logs --tail=50 rag-api"
```

### 6. Testuj API

```bash
# Health check
curl http://89.167.41.22:8000/health | python3 -m json.tool

# Test search
curl -X POST "http://89.167.41.22:8000/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"wordpress","top_k":3}' | python3 -m json.tool
```

## Potencjalne problemy

### Problem 1: AttributeError 'QueryResponse' object has no attribute 'points'

**Przyczyna:** Zapomniałeś dodać `.points` przy `query_points()`

**Rozwiązanie:**
```python
# Złe:
candidates = self.client.query_points(...)

# Dobre:
candidates = self.client.query_points(...).points
```

### Problem 2: "using parameter is required"

**Przyczyna:** Nie określiłeś `using="dense"` dla named vectors

**Rozwiązanie:**
```python
self.client.query_points(
    collection_name=self.collection_name,
    query=query_embedding.tolist(),
    using="dense",  # DODAJ TĘ LINIĘ
    ...
)
```

## Rollback (jeśli coś pójdzie nie tak)

```bash
# Przywróć starą wersję
git checkout deployment/requirements.txt search.py

# Rebuild z 1.11.3
ssh rag "cd /opt/rag-api/deployment && docker compose down && docker compose build --no-cache && docker compose up -d"
```

## Różnice w szczegółach

| Funkcja | 1.11.3 | 1.16.2 |
|---------|--------|--------|
| Metoda search | `search()` | `query_points()` |
| Metoda grouping | `search_groups()` | `query_points_groups()` |
| Parametr wektora | `query_vector=("dense", vec)` | `query=vec, using="dense"` |
| Zwracany typ (search) | `List[ScoredPoint]` | `QueryResponse.points` |
| Zwracany typ (groups) | `GroupsResult` | `GroupsResult` (bez zmian) |

## Timeline upgrade

Kiedy zaktualizować:
- **Teraz (1.11.3):** Stabilne, działa produkcyjnie
- **Za tydzień/miesiąc (1.16.2):** Gdy chcesz najnowsze features
- **Priorytet:** Średni (nie krytyczne, ale zalecane)

## Dodatkowe zasoby

- [Qdrant Client Changelog](https://github.com/qdrant/qdrant-client/releases)
- [Oficjalna dokumentacja query_points](https://python-client.qdrant.tech/qdrant_client.qdrant_client)
- [Migration Guide (oficjalny)](https://qdrant.tech/documentation/guides/migration/)
