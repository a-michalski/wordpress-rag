#!/bin/bash

# Test HF Inference API (FREE tier)
# Sprawdza czy nomic-embed-text-v1.5 działa przez router.huggingface.co

echo "=== Testing HF Inference API ==="
echo ""
echo "1. Sprawdzamy endpoint..."
echo "   URL: https://router.huggingface.co/models/nomic-ai/nomic-embed-text-v1.5"
echo ""

# Musisz podać swój HF token tutaj:
# Pobierz z: https://huggingface.co/settings/tokens
HF_TOKEN="hf_YOUR_TOKEN_HERE"

if [ "$HF_TOKEN" = "hf_YOUR_TOKEN_HERE" ]; then
    echo "❌ ERROR: Ustaw swój HF_TOKEN w pliku test_hf_api.sh (linia 12)"
    echo ""
    echo "Jak zdobyć token:"
    echo "1. Otwórz: https://huggingface.co/settings/tokens"
    echo "2. Create new token → Read access"
    echo "3. Skopiuj token i wklej w test_hf_api.sh"
    exit 1
fi

echo "2. Wysyłam request z testem embedding..."
echo ""

RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" \
  -X POST "https://router.huggingface.co/models/nomic-ai/nomic-embed-text-v1.5" \
  -H "Authorization: Bearer $HF_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inputs": "search_query: test pytanie po polsku"}')

HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d':' -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_CODE:/d')

echo "HTTP Status: $HTTP_CODE"
echo ""

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ SUCCESS! HF Inference API działa!"
    echo ""
    echo "Response (pierwsze 200 znaków):"
    echo "$BODY" | cut -c1-200
    echo "..."
    echo ""
    echo "Embedding wymiary:"
    DIMS=$(echo "$BODY" | grep -o '\[' | wc -l)
    echo "   Zwrócono embedding (powinno być ~768 wymiarów)"
    echo ""
    echo "✅ Możesz teraz użyć workflow w n8n!"
elif [ "$HTTP_CODE" = "401" ]; then
    echo "❌ ERROR: 401 Unauthorized"
    echo ""
    echo "Token niepoprawny lub wygasł. Wygeneruj nowy token:"
    echo "   https://huggingface.co/settings/tokens"
elif [ "$HTTP_CODE" = "503" ]; then
    echo "⚠️  WARNING: 503 Service Unavailable"
    echo ""
    echo "Model jest ładowany (cold start). To normalne przy pierwszym użyciu."
    echo "Poczekaj 30-60 sekund i spróbuj ponownie:"
    echo "   bash test_hf_api.sh"
else
    echo "❌ ERROR: Nieoczekiwany status $HTTP_CODE"
    echo ""
    echo "Response:"
    echo "$BODY"
fi

echo ""
echo "=== Test zakończony ==="
