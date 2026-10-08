# AI Agent Runtime Intelligence Platform

## 1. Goal

Build a backend platform for executing and observing agentic AI workflows.

The long-term goal is to build **runtime intelligence for agentic AI systems** that can:

- Detect runaway agent execution.
- Detect runtime feedback loops and non-converging behavior.
- Predict potential infinite loops.
- Predict and control runaway execution cost.
- Apply runtime safety mechanisms such as warning, throttling, pausing, or stopping executions.

The project should ultimately answer:

> **"Is this agent actually making progress, or is it looping and wasting time/tokens/money?"**

---

# 2. Core Functional Requirements

## Workflow Management

- Create workflows.
- Update workflows.
- Delete workflows.
- View workflows.
- Represent workflows as DAGs.
- Support agents, tools and LLM nodes.
- Validate workflow dependencies.
- Detect invalid static cycles.

## Workflow Execution

- Start an execution.
- Execute workflow nodes according to dependencies.
- Execute independent nodes concurrently where possible.
- Maintain execution state.
- Support cancellation.
- Support retries.
- Support timeouts.

### Run states

```text
CREATED
QUEUED
RUNNING
COMPLETED
FAILED
CANCELLING
CANCELLED
RETRYING
```

### Node states

```text
PENDING
RUNNING
SUCCESS
FAILED
RETRYING
SKIPPED
```

## Asynchronous Execution

```text
API
 ↓
Queue
 ↓
Worker
 ↓
Workflow Engine
```

- API must not execute long-running workflows directly.
- Workers execute workflows asynchronously.
- Multiple workers should be supported.
- Worker failures must not destroy durable execution state.

## Observability

Record structured execution information:

- Run ID
- Workflow ID
- Node ID
- Agent
- Tool
- LLM provider
- Model
- Start time
- End time
- Duration
- Status
- Errors
- Retry count
- Token usage
- Estimated cost
- Parent/child execution relationships

## Execution Tracing

Represent execution as a trace tree:

```text
Run
 ├── Agent
 │    ├── LLM Call
 │    └── Tool Call
 ├── Agent
 │    ├── Tool Call
 │    └── LLM Call
 └── Agent
      └── LLM Call
```

Every trace/span should contain enough information to reconstruct execution history.

## Reliability

Implement:

- Retry with exponential backoff.
- Configurable timeouts.
- Circuit breakers.
- Idempotency keys.
- Worker heartbeat.
- Stale-job detection.
- Job requeueing.
- Graceful failure handling.

## Security

Implement:

- Authentication.
- Authorization.
- API keys.
- RBAC.
- Tenant isolation.
- API-key hashing.
- Sensitive-data redaction.

Never store:

- API keys.
- Passwords.
- Secrets.
- Unnecessary personal information.
- Sensitive payloads without explicit justification.

---

# 3. Long-Term Intelligence Requirements

These are the most important future capabilities.

## Runtime Loop Detection

Detect runtime patterns such as:

```text
Agent A
 ↓
Tool B
 ↓
Agent A
 ↓
Tool B
 ↓
Agent A
 ↓
...
```

The system should detect repeated or non-converging execution behavior.

Detection signals may include:

- Repeated node sequences.
- Repeated tool calls.
- Repeated states.
- Repeated agent decisions.
- Excessive execution depth.
- Increasing token consumption.
- Retry explosions.
- Oscillating states.
- Lack of measurable progress.

## Loop Prediction

Move beyond detecting an existing loop.

Predict:

> "This execution is likely to become runaway."

Prediction should eventually use execution history and runtime signals.

## Cost Intelligence

Track:

```text
Input tokens
Output tokens
LLM calls
Tool calls
Execution duration
Estimated cost
```

Eventually support:

- Cost limits.
- Token limits.
- Maximum execution steps.
- Maximum tool calls.
- Maximum execution time.
- Projected execution cost.
- Cost anomaly detection.

Example:

```text
Current cost:       $0.42
Projected cost:     $5.80
Budget:             $5.00

WARNING: Possible runaway execution
```

## Runtime Intervention

Eventually support:

```text
WARNING
   ↓
THROTTLE
   ↓
PAUSE
   ↓
REQUIRE APPROVAL
   ↓
STOP
```

The system should make intervention configurable.

---

# 4. Non-Functional Requirements

## Scalability

- API layer should be horizontally scalable.
- Workers should scale independently.
- Execution workloads should not block API requests.
- Queue depth should be measurable.

## Reliability

- Durable execution metadata.
- Recoverable worker failures.
- At-least-once job execution should be assumed.
- Operations with external side effects should use idempotency where possible.

## Performance

Target initially:

```text
Lightweight API p95 < 200ms
```

Do not optimize prematurely.

Measure real bottlenecks through load testing.

## Availability

API availability should not depend on successful agent execution.

```text
Agent failure != API failure
```

## Security

- Tenant isolation.
- Least privilege.
- Secret protection.
- Payload redaction.
- Secure authentication.
- Authorization checks.

## Observability

The platform itself must expose:

- API latency.
- Queue latency.
- Worker utilization.
- Execution latency.
- Error rate.
- Retry rate.
- Token usage.
- Cost.
- Loop-detection events.

## Maintainability

- Clear module boundaries.
- Typed interfaces.
- Automated tests.
- Database migrations.
- Configuration through environment variables.
- Structured logging.

---

# 5. Tech Stack

## Backend

```text
Python
FastAPI
SQLAlchemy
Alembic
Pydantic
```

## Database

```text
PostgreSQL
```

Used for durable relational state:

```text
Users
Organizations
Projects
Workflows
Runs
Nodes
Traces
Spans
API Keys
Idempotency Records
```

## Queue / Temporary State

```text
Redis
```

Used for:

- Job queue.
- Rate limiting.
- Distributed coordination.
- Short-lived state.
- Caching.

Redis is NOT the primary source of truth.

## Workflow Engine

```text
Custom DAG Execution Engine
```

Implement the fundamental execution logic yourself.

LangGraph can be integrated later for comparison/integration.

## Observability

```text
OpenTelemetry
Prometheus
Grafana
```

## Frontend

```text
React
React Flow
WebSockets
```

## Infrastructure

```text
Docker
Docker Compose
Nginx
AWS EC2
```

## Testing

```text
Pytest
Locust
```

---

# 6. Basic Architecture

```text
                    React UI
                       │
                       │ HTTPS
                       ▼
                    Nginx
                       │
                       ▼
                 ┌────────────┐
                 │  FastAPI   │
                 │ Control API│
                 └─────┬──────┘
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
        PostgreSQL   Redis    WebSocket
             │         │
             │       Queue
             │         │
             │    ┌────┴────┐
             │    ▼         ▼
             │ Worker 1   Worker N
             │    │         │
             │    └────┬────┘
             │         ▼
             │   Workflow Engine
             │         │
             │    ┌────┼────┐
             │    ▼    ▼    ▼
             │  Agent Tool  LLM
             │         │
             └─────────▼
                  Trace Data
                       │
              OpenTelemetry
                 /         \
                ▼           ▼
           Prometheus     Grafana
```

---

# 7. Stepwise Development Goals

## Phase 1 — Backend Foundation

Build:

- FastAPI.
- PostgreSQL.
- SQLAlchemy.
- Alembic.
- Users.
- Projects.
- Workflows.
- Runs.

Do not add advanced infrastructure yet.

## Phase 2 — DAG Engine

Implement:

- Workflow representation.
- DAG validation.
- Topological ordering.
- Dependency resolution.
- Node execution.
- Parallel execution.
- State machine.

## Phase 3 — Async Execution

Add:

```text
FastAPI
 ↓
Redis
 ↓
Workers
 ↓
Workflow Engine
```

Implement:

- Job queue.
- Worker execution.
- Job status.
- Worker heartbeat.

## Phase 4 — Agent Execution

Add:

- Agent nodes.
- Tool nodes.
- LLM nodes.
- Tool registry.
- LLM provider abstraction.

## Phase 5 — Observability

Add:

- Execution events.
- Traces.
- Spans.
- Latency tracking.
- Token tracking.
- Cost calculation.
- Error tracking.

## Phase 6 — Reliability

Add:

- Retries.
- Exponential backoff.
- Timeouts.
- Circuit breakers.
- Idempotency.
- Stale-job detection.
- Requeueing.

## Phase 7 — Dashboard

Build:

- Workflow viewer.
- Run history.
- Execution timeline.
- Trace viewer.
- Cost dashboard.
- Error dashboard.
- Live execution using WebSockets.

## Phase 8 — Runtime Loop Detection

Start simple.

Implement:

- Execution-depth limits.
- Repeated-node detection.
- Repeated-sequence detection.
- Repeated tool-call detection.
- Runtime state tracking.

Then measure false positives and false negatives.

## Phase 9 — Cost Intelligence

Implement:

- Cost budgets.
- Token budgets.
- Cost-per-run.
- Cost-per-agent.
- Cost-per-tool.
- Cost anomaly detection.
- Projected cost.

## Phase 10 — Predictive Runtime Intelligence

Research and implement:

- Non-convergence detection.
- Loop prediction.
- Runaway-cost prediction.
- Execution-risk scoring.
- Runtime intervention.

This is the long-term research/engineering direction.

---

# 8. AI Coding Agent Rules

The AI coding agent must follow these rules.

## Rule 1 — Understand Before Coding

Before modifying code:

1. Inspect the repository.
2. Understand the existing architecture.
3. Find related modules.
4. Identify dependencies.
5. Explain the intended change internally.
6. Then implement.

Do not blindly create new files.

## Rule 2 — Follow Existing Architecture

Prefer modifying existing abstractions over creating duplicate abstractions.

Do not introduce a new framework/library unless there is a clear reason.

## Rule 3 — No Resume-Driven Architecture

Do NOT add technologies simply because they look impressive.

Avoid premature:

```text
Kafka
Kubernetes
Cassandra
Elasticsearch
ClickHouse
Microservices
Service Mesh
```

Introduce infrastructure only when a measured requirement justifies it.

## Rule 4 — Keep PostgreSQL as Source of Truth

Durable state must live in PostgreSQL.

Redis must not become the authoritative database.

## Rule 5 — Separate Control Plane and Data Plane

Control plane:

```text
Users
Projects
Workflows
Configuration
Permissions
```

Data plane:

```text
Workflow execution
Agents
Tools
LLMs
Execution events
```

Do not mix responsibilities unnecessarily.

## Rule 6 — Design for Failure

Every external dependency must have:

- Timeout.
- Error handling.
- Retry policy where appropriate.
- Logging.
- Failure state.

Assume:

```text
LLM can fail.
Tool can fail.
Redis can fail.
Worker can crash.
Database can become unavailable.
Network can fail.
```

## Rule 7 — Never Hide Complexity

Do not silently swallow errors.

Bad:

```python
try:
    ...
except:
    pass
```

Failures must be observable.

## Rule 8 — Prefer Explicit State Machines

Do not allow arbitrary execution-state mutations.

Validate state transitions.

## Rule 9 — Idempotency Matters

Any operation that can be retried must consider duplicate execution.

Never assume:

```text
request == exactly once
```

## Rule 10 — Measure Before Optimizing

Do not optimize based on assumptions.

Use:

```text
logs
metrics
profiling
load tests
```

to identify bottlenecks.

## Rule 11 — Security by Default

Never commit:

```text
API keys
tokens
passwords
secrets
```

Never log sensitive credentials.

Redact sensitive payloads.

## Rule 12 — Test Failure Scenarios

Tests must cover more than the happy path.

Test:

```text
Duplicate request
Worker crash
LLM timeout
Tool timeout
Redis failure
Database failure
Retry exhaustion
Invalid workflow
Cancellation
Concurrent execution
```

## Rule 13 — Preserve Simplicity

Prefer:

```text
simple + correct
```

over:

```text
complex + impressive
```

## Rule 14 — Explain Architectural Decisions

When introducing a significant component, document:

```text
Problem
Decision
Alternatives
Reason
Trade-offs
```

## Rule 15 — Protect the North Star

Every major feature should eventually help answer:

> **Is this agent making useful progress, or is it entering runaway execution and wasting resources?**

Do not allow the project to become merely another generic AI workflow builder.

---

# 9. Engineering Principles

```text
Correctness > Features
Reliability > Complexity
Measured performance > Assumptions
Explicit state > Hidden state
Durability > Convenience
Observability > Guessing
Simple architecture > Resume-driven architecture
Security by default
Failure is expected
Design for evolution
```

The final system should evolve from:

```text
Execute
   ↓
Observe
   ↓
Understand
   ↓
Detect
   ↓
Predict
   ↓
Prevent
```

The ultimate objective is:

> **Build infrastructure that can determine when an agentic AI system is no longer making useful progress and prevent it from consuming unbounded execution time, tokens, or money.**