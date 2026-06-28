# KIRON BROKER ENGINE - ARCHITECTURE

Versione: 1.0  
Ultimo aggiornamento: 28/06/2026

---

# Architettura generale

Il sistema è diviso in due parti:

```text
Flutter Frontend
        ↓
FastAPI Backend
        ↓
Broker Engine
        ↓
PDF Parser / AI / BankRule Engine
```

---

# Frontend Flutter

Responsabilità:

- inserimento pratica;
- import PDF banca;
- visualizzazione banche;
- preview PDF;
- gap analysis;
- risultati ricerca;
- generazione preventivo PDF.

Il frontend NON deve contenere logica bancaria complessa.

---

# Backend FastAPI

File principale:

```text
api.py
```

Responsabilità:

- ricevere richieste dal frontend;
- coordinare i servizi;
- esporre endpoint REST;
- restituire JSON strutturato.

---

# Servizi principali

```text
PdfImportService
PdfPreviewService
PdfGapAnalyzerService
PracticeService
RatesService
QuotePdfService
BankEligibilityService
BankMemoryConfirmService
```

---

# Pipeline PDF

```text
PDF originale
      ↓
PdfDocumentReader
      ↓
Page / Blocks
      ↓
PdfPreviewService
      ↓
PdfGapAnalyzerService
      ↓
BankRuleBuilder
      ↓
BankMemory
```

---

# Pipeline futura AI

```text
PDF Page Text
      ↓
AI Knowledge Extractor
      ↓
JSON strutturato
      ↓
BankRuleBuilder
      ↓
BankRule
      ↓
BankMemory
      ↓
Eligibility Engine
```

---

# Principio chiave

Il parser legge il PDF.

L'AI interpreta il significato.

Il BankRule Engine valuta la pratica.

Questi tre livelli devono restare separati.

---

# BankRule Engine

Ogni regola bancaria deve essere rappresentata da:

```text
BankRule
```

con:

```text
type
title
description
parameters
source_page
confidence
```

---

# Esempio LTC_EXCEPTION

```json
{
  "type": "LTC_EXCEPTION",
  "title": "Mutuo LTC",
  "description": "Deroga fino al 95% con perizia superiore al prezzo",
  "parameters": {
    "purchase_ltv": 95,
    "perizia_ltv": 80,
    "spread_bps": 40,
    "requires_appraisal_value": true,
    "applies_to_rate_types": ["FISSO", "VARIABILE"]
  },
  "source_page": 2,
  "confidence": 0.98
}
```

---

# Eligibility Engine

Il motore di eleggibilità non deve conoscere il layout del PDF.

Deve ricevere:

```text
Practice
BankRule[]
```

e restituire:

```text
eligible
warnings
score
extra_spread
reason
```

---

# Regola architetturale fondamentale

Non aggiungere mai logica del tipo:

```python
if banca == "CheBanca":
```

La banca deve essere descritta da BankRule, non da codice hardcoded.

---

# Dati e memoria

La memoria banca deve distinguere tra:

## Memoria documentale

Cosa era scritto nel PDF:

```text
pagina
testo
blocchi
frasi
```

## Memoria decisionale

Cosa il motore ha capito:

```text
BankRule
parameters
confidence
```

---

# Obiettivo architetturale

Rendere il sistema capace di aggiungere nuove banche senza modificare il motore centrale.

Aggiungere una banca deve significare:

```text
carico PDF
↓
estraggo regole
↓
confermo
↓
motore pronto
```

---

# Convenzione di sviluppo

Ogni nuovo modulo deve rispettare questi principi:

- singola responsabilità;
- input e output chiari;
- nessuna dipendenza dal layout specifico della banca;
- testabile isolatamente;
- compatibile con BankRule.
