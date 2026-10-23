# SignalBooks

**Telecom and network-equipment company reports explained, with cheaper models for easy questions and stronger models for hard ones.**

## Problem

ECE students attend interviews at telecom companies without knowing company-specific details such as ARPU, 5G rollout, CAPEX, and order book. The placement coordinator wants every student to use a chatbot to learn about the company and prepare for interviews. However, providing access to a powerful AI model for around 500 students can become too expensive.

SignalBooks aims to make interview preparation more affordable by routing simple questions to cheaper AI models and complex questions to stronger models while keeping answers useful and grounded in company reports.


## Who it is for
- **Primary user:** Placement-cell coordinators at engineering colleges who prepare ECE students for interviews at telecom operators and network-equipment companies.

- **End users:** ECE students who want to understand company performance, financial metrics, business developments, and industry-specific information before placement interviews.

## Signature feature
A live cost meter on every answer shows which AI model responded, the tokens used, and the cost in paise. This helps users track AI usage and understand the cost of each response.


## Hardest problem : Cost-Aware Model Routing
The main technical challenge is deciding which AI model should answer each question.

A small classifier is intended to route simple lookups, such as "What was Airtel's ARPU last quarter?", to a cheaper model. Complex questions, such as "Compare the CAPEX intensity of Airtel and Vodafone Idea", are intended to use a stronger model.

The system will track tokens and cost per query and evaluate whether this routing strategy can reduce costs while keeping answer quality within two percentage points of an always-strong-model baseline.


## Dataset

SignalBooks will use publicly available annual reports and quarterly results presentations from six telecom and network-equipment companies.

| Source | Link | Documents | Pages | Licence / terms |
|---|---|---|---|---|
| Bharti Airtel | [Investor Results](https://www.airtel.in/about-bharti/equity/results) | 3 annual reports collected (FY 2023–24, FY 2024–25, FY 2025–26); quarterly PDFs downloaded, verification pending | Not yet counted | Company-published documents; reuse terms to be checked |
| Vodafone Idea | [Official Website](https://www.myvi.in/) | Not yet collected | Not yet counted | Reuse terms to be checked |
| Indus Towers | [Investor Results](https://www.industowers.com/investor/result/) | Not yet collected | Not yet counted | Reuse terms to be checked |
| Tata Communications | [Investor Results](https://www.tatacommunications.com/investors/results) | Not yet collected | Not yet counted | Reuse terms to be checked |
| Tejas Networks | [Investor Relations](https://www.tejasnetworks.com/investor-relations/) | Not yet collected | Not yet counted | Reuse terms to be checked |
| HFCL | [Investor Financial Information](https://www.hfcl.com/investors/financial-info) | Not yet collected | Not yet counted | Reuse terms to be checked |


**Dataset target:**

- **Annual reports:** At least 18 in total, targeting three reports per company across three financial years.
- **Quarterly results presentations:** At least 40 across all six companies.
- **Total document size:** At least 6,000 pages across the collected documents.

**Note:** The target is 18 annual reports in total (three per company), not 18 per company. Quarterly PDFs will be counted toward the 40-presentation target only after verifying their reporting periods, document types, and uniqueness.


## 10 real questions
See [docs/QUESTIONS.md](docs/QUESTIONS.md).

## Run it
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                                 # Windows: copy .env.example .env
uvicorn app.main:app --reload
curl localhost:8000/health
```

## Live link
<Added in Week 2>
