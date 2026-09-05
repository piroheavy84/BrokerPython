# KIRON BROKER ENGINE - ARCHITECTURE

Versione: 1.1
Ultimo aggiornamento: 29/06/2026

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
PDF Parser
        ↓
Page Knowledge Engine
        ↓
BankRule Engine
        ↓
Eligibility Engine
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

Il frontend NON deve contenere logica bancaria.

---

# Backend FastAPI

File principale:

```text
api.py
```

Responsabilità:

- ricevere richieste;
- coordinare i servizi;
- esporre API REST;
- restituire JSON.

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
PageKnowledgeBuilder
RuleBuilder
RuleCleaner
RuleValidator
HeaderParser
```

---

# Pipeline PDF

```text
PDF originale
        ↓
PdfDocumentReader
        ↓
PageAnalyzer
        ↓
RuleBuilder
        ↓
RuleCleaner
        ↓
RuleValidator
        ↓
PageKnowledgeBuilder
        ↓
PageKnowledge
        ├── Header
        ├── Products
        ├── MarketIndexes
        ├── Costs
        ├── Conditions
        ├── Exceptions
        ├── Notes
        └── RawText
        ↓
BankRuleBuilder
        ↓
BankRule[]
        ↓
BankMemory
        ↓
Eligibility Engine
```

---

# PageKnowledge

PageKnowledge rappresenta tutta la conoscenza estratta da una singola pagina del PDF.

Non contiene logica.

Contiene solamente informazioni strutturate.

```text
PageKnowledge

page

header

products

market_indexes

costs

conditions

exceptions

notes

raw_text
```

Ogni pagina produce un solo PageKnowledge.

---

# Products

I prodotti rappresentano esclusivamente le offerte commerciali.

Esempio:

```text
Mutuo Acquisto

Fisso

Variabile

Cap

Floor

Durata

LTV

Spread
```

---

# Market Indexes

Contiene gli indici di riferimento.

Esempi:

```text
IRS

EURIBOR

BCE
```

Questi dati saranno utilizzati dal motore di calcolo tassi.

---

# Costs

Contiene tutti i costi presenti nel PDF.

Esempi:

```text
Spese istruttoria

Perizia

Incasso rata

Polizze

Commissioni
```

Questi dati saranno utilizzati dal preventivatore.

---

# Conditions

Contiene tutte le condizioni tecniche.

Esempi:

```text
CAP

FLOOR

TAN

TAEG

Periodicità

Parametro di indicizzazione
```
---

# Exceptions

Le eccezioni rappresentano regole non tabellari.

Esempi:

```text
LTC 95

GREEN

CONSAP

GARANZIE

DEROGHE
```

Queste informazioni saranno trasformate successivamente in `BankRule`.

---

# Notes

Contiene testo libero non ancora strutturato.

Serve come supporto all'AI e come audit del parser.

---

# RawText

Conserva il testo originale della pagina.

Non deve mai essere modificato.

Serve per:

- audit;
- debugging;
- AI;
- ricostruzione della pagina.

---

# Pipeline AI

```text
RawText
        ↓
AI Knowledge Extractor
        ↓
ExtractedRule[]
        ↓
BankRuleBuilder
        ↓
BankRule[]
```

L'AI interpreta il significato.

Non legge direttamente il PDF.

Lavora esclusivamente sul contenuto di `PageKnowledge`.

---

# BankRule Engine

Ogni regola bancaria deve essere rappresentata come:

```text
BankRule

type

title

description

parameters

source_page

confidence
```

Le banche NON devono essere codificate nel motore.

Il motore conosce solo `BankRule`.

---

# Esempio

```text
RuleType

LTC_EXCEPTION

Parameters

purchase_ltv_max = 95

appraisal_ltv_max = 80

spread_adjustment_bps = 40

requires_appraisal_gt_purchase = true
```

---

# Eligibility Engine

Input:

```text
Practice

+

BankRule[]
```

Output:

```text
Eligible

Warnings

Score

ExtraSpread

Reason
```

L'Eligibility Engine non deve conoscere:

- PDF
- layout
- banca
- parser

Conosce solamente le regole.

---

# Regola fondamentale

È vietato introdurre codice come:

```python
if banca == "CheBanca":
```

oppure

```python
if pdf_name == ...
```

oppure qualsiasi altra eccezione specifica.

Ogni comportamento deve derivare dalle `BankRule`.

---

# Obiettivo finale

L'aggiunta di una nuova banca dovrà essere:

```text
Carico PDF

↓

Parser

↓

PageKnowledge

↓

BankRule

↓

Conferma operatore

↓

BankMemory

↓

Eligibility Engine

↓

Preventivatore

↓

Motore esperto
```

---

# Convenzione di sviluppo

Ogni modulo deve:

- avere una sola responsabilità;
- essere testabile isolatamente;
- non conoscere banche specifiche;
- produrre input/output chiari;
- essere riutilizzabile;
- essere compatibile con `BankRule`;
- essere compatibile con `PageKnowledge`;
- ridurre il debito tecnico;
- evitare duplicazioni;
- mantenere la separazione tra Parser, AI e Motore Decisionale.

---

# Visione del progetto

KIRON Broker Engine non è un parser PDF.

È un motore esperto capace di:

- leggere documentazione bancaria;
- comprenderne il significato;
- costruire una memoria strutturata;
- trasformare la conoscenza in regole;
- valutare automaticamente l'eleggibilità delle pratiche;
- supportare il consulente senza logiche hardcoded.

Ogni evoluzione futura dovrà rispettare questa architettura.
