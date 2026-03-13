"""
benchmark.py

Runs inside each Daytona sandbox. Imports the candidate `is_prime` function,
validates correctness against a ground-truth test suite, then measures
execution time and memory usage.

Output: a single JSON object printed to stdout.
"""

import json
import sys
import time
import tracemalloc
import importlib.util
from pathlib import Path


# ---------------------------------------------------------------------------
# Ground-truth test suite
# ---------------------------------------------------------------------------

TEST_CASES = [
    (-1,           False),  # negative
    (0,            False),  # zero
    (1,            False),  # one is not prime by definition
    (2,            True),   # smallest prime
    (3,            True),   # small prime
    (4,            False),  # small composite
    (5,            True),
    (9,            False),  # 3*3
    (13,           True),
    (17,           True),
    (25,           False),  # 5*5
    (97,           True),   # two-digit prime
    (100,          False),  # round composite
    (561,          False),  # Carmichael number — tricky for naive implementations
    (1_000_003,    True),   # large prime
    (1_000_000_007, True),  # classic CS prime
    (1_000_000_008, False), # large composite
]

BENCHMARK_INPUTS = [2, 97, 1_000_003, 1_000_000_007]
BENCHMARK_RUNS = 5


# ---------------------------------------------------------------------------
# Load candidate solution
# ---------------------------------------------------------------------------

def load_is_prime(solution_path: str):
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "is_prime"):
        raise AttributeError("Solution does not define a function named 'is_prime'")
    return module.is_prime


# ---------------------------------------------------------------------------
# Correctness gate
# ---------------------------------------------------------------------------

def check_correctness(is_prime_fn) -> tuple[bool, str]:
    for n, expected in TEST_CASES:
        try:
            result = is_prime_fn(n)
        except Exception as e:
            return False, f"Exception on input {n}: {e}"
        if result != expected:
            return False, f"Wrong answer for {n}: expected {expected}, got {result}"
    return True, ""


# ---------------------------------------------------------------------------
# Performance measurement
# ---------------------------------------------------------------------------

def measure_performance(is_prime_fn) -> tuple[float, float]:
    """Returns (median_execution_time_ms, peak_memory_mb)."""
    times = []

    tracemalloc.start()
    for _ in range(BENCHMARK_RUNS):
        start = time.perf_counter()
        for n in BENCHMARK_INPUTS:
            is_prime_fn(n)
        end = time.perf_counter()
        times.append((end - start) * 1000)  # ms
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    times.sort()
    median_ms = times[BENCHMARK_RUNS // 2]
    peak_mb = peak / (1024 * 1024)
    return median_ms, peak_mb


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def compute_score(execution_time_ms: float, memory_mb: float) -> float:
    time_score = (1 / execution_time_ms) * 0.6
    mem_score = (1 / memory_mb) * 0.4 if memory_mb > 0 else 0
    return round((time_score + mem_score) * 1000, 4)


def count_lines(solution_path: str) -> int:
    return sum(1 for line in Path(solution_path).read_text().splitlines() if line.strip())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark(solution_path: str) -> dict:
    sandbox_id = Path(solution_path).stem  # e.g. "solution_007"

    try:
        is_prime_fn = load_is_prime(solution_path)
    except Exception as e:
        return {
            "sandbox_id": sandbox_id,
            "passed": False,
            "error": f"FAILED_LOAD: {e}",
            "execution_time_ms": None,
            "memory_mb": None,
            "score": 0,
            "lines_of_code": None,
        }

    passed, reason = check_correctness(is_prime_fn)
    if not passed:
        return {
            "sandbox_id": sandbox_id,
            "passed": False,
            "error": f"FAILED_CORRECTNESS: {reason}",
            "execution_time_ms": None,
            "memory_mb": None,
            "score": 0,
            "lines_of_code": count_lines(solution_path),
        }

    execution_time_ms, memory_mb = measure_performance(is_prime_fn)
    score = compute_score(execution_time_ms, memory_mb)

    return {
        "sandbox_id": sandbox_id,
        "passed": True,
        "error": None,
        "execution_time_ms": round(execution_time_ms, 4),
        "memory_mb": round(memory_mb, 6),
        "score": score,
        "lines_of_code": count_lines(solution_path),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python benchmark.py <solution_path>"}))
        sys.exit(1)

    result = run_benchmark(sys.argv[1])
    print(json.dumps(result))
