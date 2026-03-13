# Task 02 — Build the LLM Agent (Solution Generator)

## Goal
Create `agent.py` that generates 25 diverse candidate Python implementations of a prime-checking function in a **single LLM API call**.

## Decisions
- Use a single call with `n=25` (parallel completions) — one round-trip, no sequential bottleneck
- Model: `claude-sonnet-4-6` via the Anthropic SDK
- All 25 solutions are generated before any sandbox is launched

## Prompt Strategy
The prompt must encourage **meaningful diversity**, not near-duplicate outputs. Include explicit instructions to vary:
- Algorithm approach (trial division, Sieve, Miller-Rabin, etc.)
- Optimization level (simple vs. highly optimized)
- Use of stdlib vs. pure logic

## Prompt Template

```
Generate a Python function named `is_prime(n: int) -> bool` that determines
whether a number is prime.

Requirements:
- The function must be named exactly `is_prime`
- It must handle all integers including negatives, 0, and 1
- Focus on correctness first, then performance
- Use a DIFFERENT algorithmic approach than typical trial division if possible

Return ONLY the Python function definition, no explanation, no markdown.
```

Send this prompt 25 times with `temperature=1.0` to maximize diversity.

## Output
- Save each solution to `solutions/solution_001.py` through `solution_025.py`
- Log which solutions were generated successfully

## Error Handling
- If a completion returns malformed code (syntax error on parse), log and skip — do not crash
- Minimum viable run: at least 10 valid solutions

## File to Create
- `agent.py`
