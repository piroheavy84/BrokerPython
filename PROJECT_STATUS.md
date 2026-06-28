# KIRON BROKER ENGINE

Versione documento: 1.0
Ultimo aggiornamento: 28/06/2026

---

# Visione del progetto

Kiron Broker Engine è un motore professionale per mediatori creditizi.

L'obiettivo è costruire un sistema capace di:

- leggere automaticamente i PDF delle banche;
- interpretare le regole dei prodotti;
- memorizzare la conoscenza bancaria;
- valutare automaticamente l'eleggibilità delle pratiche;
- confrontare decine di mutui;
- produrre preventivi professionali;
- imparare nuovi listini senza modificare il codice.

Il progetto deve diventare indipendente dal formato dei PDF.

---

# Stack tecnologico

## Frontend

- Flutter
- Riverpod

## Backend

- Python 3.14
- FastAPI
- Uvicorn

## Parsing PDF

- pdfplumber
- BeautifulSoup
- pandas

## Output

- ReportLab
- JSON

## Versionamento

- Git
- GitHub

---

# Stato attuale

## Backend

✅ API FastAPI funzionante

✅ Parser PDF funzionante

✅ Preview PDF

✅ Gap Analysis

✅ Indicizzazione prodotti

✅ Ranking prodotti

✅ Generazione preventivi PDF

✅ Registro preventivi

✅ Registro clienti

✅ Calcolo tassi

✅ Memoria banca

---

## Frontend

✅ Dashboard

✅ Import PDF

✅ Gestione banche

✅ Nuova pratica

✅ Risultati ricerca

✅ Preventivo PDF

---

# Componenti principali

services/

- PdfImportService
- PdfPreviewService
- PdfGapAnalyzerService
- PracticeService
- RankingService
- QuotePdfService
- RatesService
- BankEligibilityService
- BankMemoryService
- BankMemoryConfirmService

---

# Evoluzione architetturale

Il progetto NON dovrà più salvare solamente testo estratto.

Il parser dovrà produrre una rappresentazione strutturata della conoscenza bancaria.

La nuova pipeline sarà:

PDF

↓

Parser

↓

AI Knowledge Extractor

↓

BankRule

↓

Bank Memory

↓

Eligibility Engine

↓

Broker Engine

---

# Modello BankRule

Ogni regola bancaria sarà rappresentata tramite:

- tipo
- titolo
- descrizione
- parametri
- pagina origine
- confidence

Le regole saranno indipendenti dalla banca.

---

# RuleType attualmente previsti

- LTV
- LTC_EXCEPTION
- SPREAD
- RATE
- DURATION
- PURPOSE
- PROPERTY
- AGE
- CONSAP
- GREEN
- GUARANTEE
- DEROGATION
- NOTE

---

# Primo caso implementato

CheBanca

Pagina 2

Caso:

LTC Exception

Descrizione:

Mutuo finanziabile fino al 95% del prezzo di acquisto quando il valore di perizia consente di rispettare l'80% sulla perizia.

Extra spread:

+40 bps

Questa regola NON rappresenta un nuovo prodotto ma una deroga.

---

# Decisioni architetturali

- Nessuna eccezione hardcoded.
- Nessuna logica specifica della banca all'interno del motore.
- Tutta la conoscenza deve essere rappresentata tramite BankRule.
- L'AI deve produrre dati strutturati, non testo libero.
- Il motore deve essere indipendente dal layout dei PDF.

---

# Modalità di sviluppo

Per ogni modifica:

1. Analisi
2. Implementazione
3. Test
4. Commit
5. Push

Mai modificare più componenti senza test intermedi.

---

# Prossima milestone

Refactoring completo del parser affinché ogni pagina venga trasformata automaticamente in una lista di BankRule.

Successivamente inizierà l'analisi sistematica di tutti i PDF banca.

---

# Roadmap sintetica

✔ Parser PDF

✔ Import PDF

✔ Preview PDF

✔ Gap Analysis

✔ Ranking

✔ Preventivi PDF

✔ Memoria banca

⬜ AI Knowledge Extractor

⬜ Universal Rule Engine

⬜ Regole bancarie automatiche

⬜ CRM

⬜ Dashboard avanzata

⬜ Versioning listini

⬜ Multi banca completo

---

# Obiettivo finale

Costruire il primo motore esperto per il broker creditizio che apprende automaticamente le regole delle banche a partire dai loro listini PDF.
