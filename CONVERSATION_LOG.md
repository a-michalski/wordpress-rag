# RAG System - Historia Rozmowy

**Data**: 19-20 stycznia 2026  
**Projekt**: RAG dla polskich artykułów technicznych z WordPress

---

## 📋 Podsumowanie Projektu

### Cel
Zbudowanie kompletnego systemu RAG (Retrieval-Augmented Generation) dla polskich artykułów technicznych eksportowanych z WordPress XML, zoptymalizowanego dla MacBook M1 16GB RAM.

### Architektura
- **Parsing**: WordPress XML → Markdown
- **Chunking**: Semantic chunking z LlamaIndex (SemanticSplitterNodeParser)
- **Embeddingi**: 3 named vectors (dense, ColBERT, sparse)
- **Baza wektorowa**: Qdrant z binary quantization
- **Wyszukiwanie**: Two-stage hybrid search z ColBERT reranking
- **Agent**: Agentic RAG z filtrami kategorii/daty

---

## 📁 Stworzone Pliki

| Plik | Opis |
|------|------|
| `config.py` | Konfiguracja (modele, ścieżki, parametry) |
| `parser.py` | Parser WordPress XML → Markdown |
| `chunker.py` | Semantic chunking z detekcją sekcji |
| `embeddings.py` | FastEmbed wrappery (dense, ColBERT, sparse) |
| `qdrant_setup.py` | Inicjalizacja kolekcji Qdrant |
| `ingest.py` | Batch ingestion (oryginalna wersja) |
| `ingest_resume.py` | Incremental ingestion z checkpoint po każdym artykule |
| `search.py` | Two-stage hybrid search |
| `agent.py` | Agentic workflow z filtrami |
| `main.py` | CLI interface |
| `migrate_to_cloud.py` | Migracja local → Qdrant Cloud |
| `requirements.txt` | Zależności Python |
| `README.md` | Dokumentacja |

---

## 🔧 Modele Embedding

| Typ | Model | Wymiar |
|-----|-------|--------|
| Dense | `nomic-ai/nomic-embed-text-v1.5` | 768 |
| ColBERT | `answerdotai/answerai-colbert-small-v1` | 96 |
| Sparse | `Qdrant/bm25` | - |

---

## 🐛 Naprawione Błędy

### 1. Batch Processing Problem
**Problem**: Oryginalny `ingest.py` chunknował WSZYSTKIE artykuły przed zapisem. Komputer się zawiesił po ~60% i 8 godzin pracy stracone.

**Rozwiązanie**: Stworzono `ingest_resume.py` z incremental processing:
- 1 artykuł → chunk → embed → SAVE → gc.collect()
- Checkpoint po każdym artykule
- Resume od ostatniego zapisanego

### 2. Import Error - QueryVector
**Problem**: `QueryVector` nie istnieje w `qdrant_client.models`

**Rozwiązanie**: Usunięto nieużywany import

### 3. Memory Killed (OOM)
**Problem**: macOS zabija proces z powodu braku RAM

**Rozwiązanie**: 
- Dodano `gc.collect()` po każdym artykule
- Dodano `gc.collect()` co 10 artykułów
- Użytkownik może uruchomić skrypt wielokrotnie (resume działa)

### 4. Variable Access Error
**Problem**: `cannot access local variable 'points' where it is not associated with a value`

**Rozwiązanie**: Inicjalizacja zmiennych przed blokiem `try`:
```python
chunks = None
points = None
```

### 5. Brak Output w Terminalu
**Problem**: Print nie pokazuje się w real-time

**Rozwiązanie**: Dodano `flush=True` do wszystkich `print()`

### 6. Sparse Vector Format
**Problem**: Sparse vector jako dict zamiast `SparseVector`

**Rozwiązanie**: Użycie `SparseVector(indices=..., values=...)`

### 7. Migration Record → PointStruct
**Problem**: `scroll()` zwraca `Record`, `upsert()` wymaga `PointStruct`

**Rozwiązanie**: Funkcja konwersji:
```python
def record_to_point(record):
    return PointStruct(
        id=record.id,
        payload=record.payload,
        vector=record.vector
    )
```

---

## 📊 Statystyki Ingestion

| Etap | Artykuły | Punkty |
|------|----------|--------|
| Start | 0 | 0 |
| Po pierwszym crash | 167 | 2076 |
| Po drugim crash | 262 | 3838 |
| **Koniec** | **399** | **7725** |

---

## ☁️ Migracja do Qdrant Cloud

### Konfiguracja
```python
QDRANT_URL = "https://79a7ee05-96b9-4ab0-8670-25d5b081a97d.europe-west3-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "...")
```

### Zmiany w kodzie
1. `config.py` - dodano `QDRANT_URL` i `QDRANT_API_KEY`
2. `qdrant_setup.py` - `create_qdrant_client()` przekazuje `api_key`
3. `migrate_to_cloud.py` - skrypt kopiujący local → cloud

---

## 🚀 Użycie

### Wyszukiwanie
```bash
python main.py search "jak skonfigurować Kubernetes"
```

### Agent
```bash
python main.py agent "Jakie są najlepsze praktyki dla Docker?"
```

### Interaktywny tryb
```bash
python main.py
```

---

## 📝 Kluczowe Lekcje

1. **Incremental saves są kluczowe** - nigdy nie procesuj wszystkiego przed zapisem
2. **ColBERT embedding używa dużo RAM** - multivector dla każdego tokena
3. **gc.collect() pomaga** - ale nie gwarantuje uniknięcia OOM
4. **Resume capability** - skrypt musi być idempotentny
5. **flush=True** - dla real-time output w Python

---

## 🔐 Uwaga Bezpieczeństwa

API key został przypadkowo udostępniony w rozmowie. **Należy wygenerować nowy API key w Qdrant Cloud!**

---

*Wygenerowano automatycznie przez GitHub Copilot*
