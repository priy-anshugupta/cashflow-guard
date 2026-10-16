# Model Usage & Cost Report

**Challenge:** HackerRank Orchestrate (September 2026) — Buy or Wait?  
**Execution Timestamp:** 2026-09-13T07:23:04Z  
**Total Evaluation Requests Processed:** 250  
**Total Pipeline Execution Time:** 121.18s  

---

## 1. Model Architecture & Providers

| Component | Model Name | Provider | Mode / Optimization |
|---|---|---|---|
| Multimodal OCR | `gpt-5.4` | OpenAI | Live Multimodal API + Schema Validation |
| Message Classification | `gpt-5.4` | OpenAI | Live Batched NLP API + Adversarial Defense |
| Cashflow Ledger Simulator | Deterministic Python Engine | Native | 0 tokens (Exact Math) |
| Plan Generator & Ranker | Spec 6-Level Priority Hierarchy | Native | 0 tokens (Exact Logic) |

---

## 2. Token Breakdown & Model Calls

| Category | Model Calls | Input Tokens | Output Tokens | Total Tokens | Cache Hits | Cache Misses | Failures |
|---|---|---|---|---|---|---|---|
| Vision OCR (`gpt-5.4`) | 16 | 23,917 | 351 | 24,268 | 0 | 16 | 0 |
| NLP Classification (`gpt-5.4`) | 9 | 17,651 | 10,614 | 28,265 | 0 | 213 | 0 |
| **Total Full-Dataset Run** | **25** | **41,568** | **10,965** | **52,533** | **0** | **229** | **0** |

---

## 3. Per-Request Efficiency & Financial Cost

- **Average Input Tokens / Request:** 166.3
- **Average Output Tokens / Request:** 43.9
- **Average Total Tokens / Request:** 210.1
- **Estimated Total Cost (USD):** $0.2684
- **Estimated Cost / Request (USD):** $0.001074

---

## 4. Verification & Reproducibility Notice

All token counts reflect the production run of the final dataset pipeline using live OpenAI API calls. Zero external API keys or credentials are included in this artifact per Section 6.5 of the challenge rules.
