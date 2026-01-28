# WordPress RAG System

System RAG (Retrieval-Augmented Generation) zoptymalizowany dla M1 Mac (16GB RAM) do analizy polskich artykułów technicznych z WordPressa.

## 🎯 Główne Funkcje

- **Hybrid Search**: 3 typy wektorów (dense, ColBERT, sparse/BM25)
- **Binary Quantization**: Kompresja 32x dla optymalizacji pamięci
- **Semantic Chunking**: Inteligentne dzielenie z zachowaniem kontekstu
- **Section Detection**: Automatyczne rozpoznawanie TL;DR, checklistów, key insights
- **Agentic Workflow**: Filtrowanie po tagach, datach, typach sekcji
- **ColBERT Reranking**: Precyzyjne dopasowanie na poziomie tokenów

## 📋 Wymagania

- Python 3.9+
- MacBook M1/M2 z 16GB RAM (lub więcej)
- Qdrant (lokalny lub zdalny)

## 🚀 Instalacja

### 1. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 2. Zainstaluj Qdrant (opcjonalnie - dla lokalnego)

```bash
# Docker
docker pull qdrant/qdrant
docker run -p 6333:6333 qdrant/qdrant

# Lub użyj wbudowanego storage (domyślnie)
```

## 📁 Struktura Projektu

```
RAG/
├── WordPress.xml           # Plik WXR z WordPressa
├── config.py              # Konfiguracja systemu
├── parser.py              # Parser WXR → Markdown
├── chunker.py             # Semantic chunking
├── embeddings.py          # FastEmbed wrappers
├── qdrant_setup.py        # Inicjalizacja kolekcji
├── ingest.py              # Pipeline ingestii
├── search.py              # Dwuetapowe wyszukiwanie
├── agent.py               # Agentic workflow
├── main.py                # CLI interface
├── requirements.txt       # Zależności
└── README.md             # Dokumentacja
```

## 🔧 Konfiguracja

Edytuj `config.py` aby dostosować:

- **Modele**: Wybór modeli embedding (dense, ColBERT, sparse)
- **Chunking**: Rozmiar chunków, overlap, breakpoint threshold
- **Search**: Limity recall/rerank, grouping settings
- **Quantization**: On/off, typ kwantyzacji

### Kluczowe Parametry

```python
# Modele (FastEmbed)
DENSE_MODEL_NAME = "nomic-ai/nomic-embed-text-v1.5"  # 768 dim
COLBERT_MODEL_NAME = "answerdotai/answerai-colbert-small-v1"  # 96 dim
SPARSE_MODEL_NAME = "Qdrant/bm25"

# Optymalizacja pamięci
ENABLE_BINARY_QUANTIZATION = True  # 32x kompresja
DENSE_VECTORS_ON_DISK = True       # Oryginalne na dysku
QUANTIZATION_ALWAYS_RAM = True     # Skwantyzowane w RAM

# Wyszukiwanie
RECALL_LIMIT = 100                 # Kandydaci do rerankingu
FINAL_RESULTS_LIMIT = 10          # Finalne wyniki
ENABLE_GROUPING = True            # Różnorodność (1 chunk/dokument)
```

## 📖 Użycie

### 1. Ingestia Dokumentów

```bash
# Parsuj WordPress XML i załaduj do Qdrant
python main.py ingest --recreate

# Użyj własnej ścieżki XML
python main.py ingest --xml-path /path/to/export.xml
```

**Pipeline ingestii:**
1. Parse WXR → ekstrahuje metadata, konwertuje HTML → Markdown
2. Semantic Chunking → dzieli z zachowaniem kontekstu
3. Embedding → generuje 3 typy wektorów (dense, ColBERT, sparse)
4. Upload → wstawia do Qdrant z payload indexami

### 2. Wyszukiwanie Semantyczne

```bash
# Proste wyszukiwanie
python main.py search "Jak używać agentów AI w developmencie?"

# Z limitem wyników
python main.py search "Product management best practices" --top-k 5
```

### 3. Wyszukiwanie z Filtrami (Agent)

```bash
# Filtruj po tagach
python main.py query "AI agents" --tags AI "#AI" "product management"

# Filtruj po kategoriach
python main.py query "UX design" --categories Design Produkt

# Filtruj po datach
python main.py query "Najnowsze trendy" --start-date 2025-01-01

# Filtruj po typach sekcji (checklist, tldr, key_insight)
python main.py query "Workflow" --section-types checklist tldr

# Kombinacja filtrów
python main.py query "AI w produktach" \
  --tags AI \
  --categories Produkt \
  --start-date 2024-01-01 \
  --section-types content key_insight \
  --top-k 10
```

### 4. Info o Kolekcji

```bash
# Pokaż statystyki kolekcji
python main.py info
```

## 🧪 Testowanie Modułów

Każdy moduł można testować osobno:

```bash
# Test parsera
python parser.py

# Test chunkera
python chunker.py

# Test embeddingów
python embeddings.py

# Test Qdrant setup
python qdrant_setup.py

# Test wyszukiwania
python search.py

# Test agenta
python agent.py
```

## 🏗️ Architektura

### Named Vectors w Qdrant

```
wordpress_articles collection:
├── dense (768 dim, Cosine)
│   └── Binary Quantization (32x compression)
├── colbert (96 dim, MaxSim)
│   └── Multivector (token-level)
└── sparse (BM25)
    └── Keyword matching
```

### Dwuetapowe Wyszukiwanie

**Stage 1: Dense Recall**
- Top-100 kandydatów przez dense vector search
- `group_by(document_id, group_size=1)` dla różnorodności
- Szybkie (quantized vectors w RAM)

**Stage 2: ColBERT Reranking**
- MaxSim scoring na kandydatach
- Token-level precision
- Top-10 finalnych wyników

### Semantic Chunking

```python
SemanticSplitterNodeParser:
  - breakpoint_percentile_threshold=85
  - buffer_size=1
  - Wykrywa typy sekcji: tldr, checklist, key_insight
```

## 🔍 Przykłady Użycia Python API

### Prosty Search

```python
from search import search

results = search(
    query="Jak zbudować zespół produktowy?",
    top_k=5
)

for result in results:
    print(f"{result.title} (score: {result.score:.3f})")
    print(f"  {result.text[:200]}...\n")
```

### Search z Filtrem

```python
from agent import search_with_agent

results = search_with_agent(
    query="AI w product management",
    top_k=10,
    tags=["AI", "product management"],
    categories=["Produkt"],
    start_date="2024-01-01",
    section_types=["content", "key_insight"]
)
```

### Użycie Agent API

```python
from agent import SearchAgent

agent = SearchAgent()

# Ustaw filtry
agent.filter_by_tags(["AI", "automation"])
agent.filter_by_date_range(start_date="2024-01-01")
agent.filter_by_section_type(["checklist"])

# Wyszukaj
results = agent.semantic_search(
    query="Workflow dla AI development",
    top_k=5
)
```

## 📊 Optymalizacja Pamięci

### Bez Optymalizacji
- Dense vectors: 768 dim × 4 bytes = 3KB per chunk
- 10,000 chunks = **30 MB**
- + ColBERT multivectors = **~100 MB**

### Z Binary Quantization
- Quantized: 768 dim ÷ 32 = 96 bytes per chunk
- 10,000 chunks = **~1 MB** (w RAM)
- Oryginalne: na dysku (lazy load)
- **Kompresja: 32x**

## 🎛️ Section Types

System rozpoznaje następujące typy sekcji:

- **`tldr`**: Podsumowania TL;DR
- **`checklist`**: Listy kontrolne, kroki
- **`key_insight`**: Kluczowe wnioski
- **`content`**: Główna treść artykułu
- **`source_attribution`**: Przypisy źródeł

## 🐛 Troubleshooting

### Problem: Brak wyników wyszukiwania
```bash
# Sprawdź kolekcję
python main.py info

# Zweryfikuj czy dokumenty zostały załadowane
# Jeśli points_count = 0, uruchom ingestię ponownie
python main.py ingest --recreate
```

### Problem: Out of Memory
```python
# W config.py zmniejsz batch size
EMBEDDING_BATCH_SIZE = 16  # zamiast 32
UPLOAD_BATCH_SIZE = 50     # zamiast 100
```

### Problem: Wolne wyszukiwanie
```python
# W config.py włącz quantization i on-disk
ENABLE_BINARY_QUANTIZATION = True
DENSE_VECTORS_ON_DISK = True
QUANTIZATION_ALWAYS_RAM = True
```

## 📚 Źródła i Technologie

- **Qdrant**: https://qdrant.tech/
- **FastEmbed**: https://github.com/qdrant/fastembed
- **LlamaIndex**: https://www.llamaindex.ai/
- **ColBERT**: https://github.com/stanford-futuredata/ColBERT
- **nomic-embed**: https://huggingface.co/nomic-ai/nomic-embed-text-v1.5

## 📝 Licencja

MIT License

## 🤝 Kontakt

Dla pytań i sugestii: michalski.adam@gmail.com
