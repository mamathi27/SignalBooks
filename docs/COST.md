# SignalBooks – LLM Cost Tracking

## 1. Purpose

SignalBooks tracks the cost of LLM requests to understand how much each question costs and how model selection affects overall spending.

The application records:
- LLM provider
- Model name
- Input tokens
- Output tokens
- Request latency
- Estimated cost in paise
- Whether fallback was used
- Whether token usage was estimated

## 2. Cost Calculation

SignalBooks calculates the estimated request cost using the following formula:

**Cost in INR:**

```text
Cost (INR) =
(Input Tokens × Input Price per Million
 + Output Tokens × Output Price per Million)
 / 1,000,000
 × USD to INR Rate
```

**Cost in paise:**

```text
Cost (Paise) = Cost (INR) × 100
```

The application uses configurable pricing values from environment variables.

## 3. Configuration

Example configuration from `.env.example`:

```env
LLM_PROVIDER=fake
LLM_MODEL=gpt-4o-mini
LLM_FALLBACK_MODEL=fake-fallback

PRICE_INPUT_PER_MILLION=0.15
PRICE_OUTPUT_PER_MILLION=0.60
USD_TO_INR_RATE=85.0
ESTIMATED_CHARS_PER_TOKEN=4
```

These pricing and currency-conversion values are illustrative configuration values, not verified live prices or exchange rates.

For real provider usage, update the prices and exchange rate using the provider's current published pricing.

Never commit the actual `.env` file or API keys.

## 4. Token Usage

When the LLM provider returns token usage, SignalBooks uses the provider-reported input and output token counts.

If the provider does not return usage information, the application estimates token counts using:

```text
Estimated Tokens = Text Length / Characters Per Token
```

The default estimate is four characters per token.

Estimated usage is marked using the `usage_estimated` field so that estimated values are not confused with provider-reported usage.

## 5. Usage Monitoring

The `/usage` endpoint provides usage information, including:

- Total number of requests
- Total cost in paise
- Number of requests with estimated token usage
- Daily request counts
- Daily token usage
- Daily cost

Use the endpoint to understand how usage changes over time.

## 6. Cost Analysis

Use the following formulas to evaluate spending:

```text
Average Cost Per Question =
Total Cost / Total Requests
```

```text
Estimated Cost for 1,000 Questions =
Average Cost Per Question × 1,000
```

Record the actual values returned by `/usage` during testing. Do not assume that the example configuration represents actual provider spending.

## 7. Cost Optimization Strategy

SignalBooks can reduce LLM spending through:

1. **Model routing:** Use a lower-cost model for simple questions and a stronger model for complex research questions.
2. **Token optimization:** Avoid sending unnecessary document content to the LLM.
3. **Retrieval optimization:** Retrieve only the relevant document sections instead of passing entire reports.
4. **Caching:** Reuse answers for repeated questions when the underlying information has not changed.
5. **Fallback handling:** Use fallback mechanisms when the primary provider experiences transient failures.

## 8. Evaluation Goals

During evaluation, compare:

- Average cost per question
- Total token consumption
- Response latency
- Answer quality
- Fallback frequency

The objective is to reduce cost while maintaining answer quality and reliable source-based responses.

