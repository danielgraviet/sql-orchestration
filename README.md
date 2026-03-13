
# The Daytona-500

Run **500 parallel AI code experiments** safely using sandbox infrastructure.

This demo shows how AI agents can explore solution spaces by launching **hundreds of isolated execution environments** in parallel, evaluating each attempt, and selecting the best result.

Instead of trying one solution at a time, the agent behaves like it has **500 brains working simultaneously**.

---

## Why This Demo Exists

Most AI agents today follow a sequential workflow:

```
generate code
run code
evaluate result
retry
```

This approach is slow and fragile.

The **500-Brain Agent** demonstrates a better pattern:

```
generate many solutions
run them in parallel
evaluate results
select the best one
```

By running experiments inside disposable sandboxes, the agent can safely test **untrusted AI-generated code at massive scale**.

---

## Architecture

```
+---------------------------+
|         LLM Agent         |
|  Generates code variants  |
+------------+--------------+
             |
             v
+---------------------------+
|       Orchestrator        |
|  Launches sandbox workers |
+------------+--------------+
             |
             v
+--------------------------------------+
|          Sandbox Workers             |
| 500 isolated environments executing  |
| generated code and returning scores  |
+--------------------------------------+
```

Each sandbox:

* receives a generated solution
* executes it
* runs benchmark tests
* reports the results

The orchestrator then chooses the best-performing solution.

---

## Demo Problem

The agent attempts to solve a programming challenge:

**Write the fastest Python function to detect whether a number is prime.**

Instead of producing a single implementation, the agent generates **hundreds of candidate solutions** and evaluates them in parallel.

---

## Features

* Parallel execution across **500+ sandboxes**
* Safe execution of **AI-generated code**
* Automatic benchmarking and scoring
* Failure isolation
* Real-time execution metrics

Example metrics during execution:

```
Sandboxes launched: 500
Running: 500
Completed: 213
Failed: 17
Average runtime: 2.4s
```

---

## Repository Structure

```
.
├── agent.py
├── orchestrator.py
├── benchmark.py
├── prompts
│   └── generate_solution.txt
├── solutions
│   └── generated code variants
├── sandbox_runner.py
└── README.md
```

### Key Components

**agent.py**

Generates candidate code implementations using an LLM.

**orchestrator.py**

Launches sandbox environments and distributes workloads.

**sandbox_runner.py**

Executes candidate code inside a sandbox and runs benchmarks.

**benchmark.py**

Test suite used to evaluate each candidate implementation.

---

## How It Works

### 1. Generate Code Variants

The agent generates multiple candidate implementations.

Example prompt:

```
Generate a Python function to determine if a number is prime.
Focus on performance.
```

Outputs are saved as:

```
solution_001.py
solution_002.py
solution_003.py
...
```

---

### 2. Launch Parallel Sandboxes

The orchestrator launches sandbox environments for each candidate.

Example workflow:

```python
for solution in solutions:
    launch_sandbox(solution)
```

Each sandbox runs independently.

---

### 3. Execute and Benchmark

Inside each sandbox:

1. The candidate code is executed
2. Benchmark tests are run
3. Performance metrics are recorded

Example output:

```
Accuracy: PASS
Execution time: 1.81ms
Memory usage: 4.2MB
Score: 97
```

Failures are isolated and reported without affecting other runs.

---

### 4. Select Best Solution

Results from all sandboxes are aggregated.

The orchestrator ranks candidates based on:

* correctness
* execution speed
* resource usage

The best implementation is returned.

---

## Safety

Running AI-generated code locally can be dangerous.

Examples of problematic behaviors:

```
rm -rf /
while True: pass
pip install malicious-package
```

Sandbox environments provide:

* filesystem isolation
* process containment
* resource limits
* disposable execution environments

Each sandbox is destroyed after execution.

---

## Observability

During execution, the system surfaces metrics such as:

```
sandboxes_running
sandbox_success_rate
average_runtime
estimated_cost
```

This allows developers to monitor large-scale agent experimentation in real time.

---

## Key Idea

Instead of relying purely on reasoning, AI agents can combine reasoning with **large-scale experimentation**.

Sandbox infrastructure enables agents to:

* run untrusted code safely
* explore many ideas simultaneously
* evaluate results quickly
* improve outcomes through search

---

## Running the Demo

Example workflow:

```
python agent.py
```

This will:

1. Generate candidate solutions
2. Launch sandbox environments
3. Execute benchmarks
4. Display the best-performing solution

---

## Expected Output

```
Launching 500 sandboxes...

Completed: 500
Successful: 463
Failed: 37

Best Solution
-------------
Accuracy: 100%
Execution Time: 1.41ms
Sandbox: 341
```

---

## Use Cases

This architecture applies to many agent workflows:

* automated code generation
* scientific experimentation
* algorithm discovery
* fuzz testing
* data analysis
* secure execution of AI-generated programs

---

## Takeaway

AI agents increasingly need to **write and execute code**.

To do this safely and efficiently, they require infrastructure that supports:

* isolated execution
* disposable environments
* large-scale parallel experimentation

Sandbox orchestration provides this missing layer in the **AI agent stack**.
