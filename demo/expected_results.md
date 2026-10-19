# Expected Results for Demo Fixtures

Fixtures are synthetic examples for upload-validation demonstrations, not financial advice or production data.

| File | Expected behaviour |
| --- | --- |
| `sample_transactions_clean.csv` | Auto-detect `transactions`; all rows have required columns, valid dates, numeric non-negative amounts and inflow/outflow direction. Validation should accept it. |
| `sample_transactions_invalid.csv` | Validation should reject rows with a malformed date, non-numeric amount or negative amount and show row/column errors; it must not silently accept the bad values. |
| `sample_transactions_formula.csv` | Formula-like description is kept as text with a leading apostrophe in cleaned data and a neutralization warning; it is never evaluated. |
| `sample_transactions_prompt_injection.csv` | The instruction-like description remains ordinary untrusted text. Upload validation may accept it as a description, but Copilot evidence must exclude it and the application must not treat it as an instruction. |

The sample files use the transaction schema in `services/validation.py`: `transaction_id,date,description,category,amount,direction,balance_after`. See `tests/test_validation.py` for parser and formula-neutralization checks.