#SolDefense (ExaSentinel)

**Next-generation, dataflow-aware PII guardrails and runaway-agent protection for AI agents querying Exasol.**

Empower your autonomous AI agents with the freedom to query your database while completely eliminating the risks of data leakage and query loop flooding.

## Problem

AI agents with database access have two failure modes:

1. **Data leakage** — a naive guardrail that blocks queries by matching column
   names (`SELECT ssn FROM ...`) is trivially defeated by an agent that renames
   the column in-query: `WITH secret AS (SELECT ssn AS code FROM customers) SELECT code FROM secret`.
   The word `ssn` never appears in the final projection, so a name-matching
   filter sees nothing wrong and raw SSNs leak.

2. **Runaway agents** — a buggy or looping agent can hammer the database with
   the same failing query dozens of times a second, degrading service for every
   other agent sharing the connection pool.

Both failure modes share a root cause: **enforcement that lives outside the
database can be skipped**, either by an agent that gets raw credentials and
connects directly, or by any request path nobody thought to instrument.

## Solution

Three components:

| Component | What it does | Where it runs | Defends against |
|---|---|---|---|
| **A. Neon Dye Taint Engine** | Parses every query into a full AST with `sqlglot`, tags sensitive root columns, and tracks that dye through aliases, CTEs, joins, and expressions — masking the output wherever the dye ends up | Python service in front of Exasol | Disguised / renamed-column leakage |
| **B. In-DB Preprocessor** | `SQL_PREPROCESSOR_SCRIPT` written in Lua, running inside the Exasol engine on every session, that rejects direct raw-column access and cannot be turned off because `ALTER SESSION` / `ALTER SYSTEM` are revoked from the agent role | Inside the Exasol engine | "Just connect directly and skip the proxy" bypass |
| **C. In-DB UDF Loop Detector** | Every proxy query is logged to `DEMO.QUERY_LOG`; a native Python UDF (`DEMO.LOOP_DETECTOR`) runs windowed aggregation over that log to detect flooding agents and writes offending `agent_id`s to `DEMO.SUSPENDED_AGENTS` | Inside the Exasol engine (UDF), triggered by an external lightweight scheduler | Runaway / looping agents degrading shared performance |

## Exasol Personal Usage

This project runs entirely on **Exasol Personal Edition** deployed via
**Local Docker**. Exasol Personal is used as:

- The primary data platform holding all demo data (`sql/01_schema_and_seed_data.sql`)
- The execution engine for the native Lua preprocessor (`sql/06_lua_preprocessor.sql`)
- The execution engine for the native Python UDF loop detector (`udf/loop_detector_udf.sql`)

## Table naming

| Table | Writer | Reader | Purpose |
|---|---|---|---|
| `DEMO.QUERY_LOG` | `proxy/suspension_client.py` | `proxy/scheduler.py`, `DEMO.LOOP_DETECTOR` UDF | Proxy query audit log used for loop detection |
| `DEMO.LOOP_QUERY_LOG` | `DEMO.SQL_GUARD` preprocessor (Lua) | `DEMO.SQL_GUARD` | Per-session fingerprint rate-limit log (internal to preprocessor) |
| `DEMO.SUSPENDED_AGENTS` | `proxy/scheduler.py` | `proxy/suspension_client.py` | Blacklist of agents suspended by loop detector |

## Setup

```bash
# 1. Start Exasol Personal
docker compose up -d exasol

# 2. Apply all SQL migrations (waits for Exasol to be ready automatically)
# On macOS/Linux:
./scripts/init_all.sh
# On Windows:
python scripts/init_all.py

# 3. Start proxy + scheduler
docker compose up -d proxy scheduler

# 4. Run the full demo matrix
python tests/run_demo_matrix.py
```

Copy `.env.example` to `.env` and fill in passwords before running.

## Running the Demo

```bash
python tests/run_demo_matrix.py
```

All 5 scenarios should print `PASS`:

| # | Scenario | Proves |
|---|---|---|
| 1 | Simple sensitive column via proxy | Component A works at all |
| 2 | Disguised via alias + CTE | Component A catches what name-matching filters miss |
| 3 | Direct connection, bypassing proxy | Component B closes the bypass |
| 4 | Agent tries to disable the guard | Grant lockdown makes Component B un-disableable |
| 5 | Agent floods identical queries | Component C detects and suspends the agent |

## Offline Taint Demo (no Docker needed)

```bash
python demo_taint.py
```

**Output:**
```text
============================================================
TEST 1: Simple column
Rewritten SQL: SELECT '***-**-****' AS SSN FROM DEMO.CUSTOMERS
Masked columns: ['SSN']

============================================================
TEST 2: Alias disguise (ssn AS secret_id)
Rewritten SQL: SELECT '***-**-****' AS SECRET_ID FROM DEMO.CUSTOMERS
Masked columns: ['SECRET_ID']

============================================================
TEST 3: Sneaky CTE attack
Rewritten SQL: WITH secret AS (SELECT ssn AS code FROM DEMO.CUSTOMERS) SELECT '***-**-****' AS CODE FROM secret
Masked columns: ['CODE']

============================================================
TEST 4: Safe column (name) - should NOT be masked
Rewritten SQL: SELECT name FROM DEMO.CUSTOMERS
Masked columns: []
```

## 🚀 Advantages Over Existing Defenses

Traditional database security mechanisms fall short against unpredictable, autonomous AI agents. SolDefense introduces a robust, multi-layered approach that outpaces conventional defenses:

1. **True Dataflow Tracking vs. Naive String Matching**: Standard SQL proxies try to block PII by matching column names. AI agents easily bypass this by renaming columns in CTEs or using complex aliases. SolDefense builds a complete Abstract Syntax Tree (AST) of the query and tracks the "taint" of sensitive data through every transformation, ensuring it is masked no matter what it is called in the final projection.
2. **Un-bypassable In-Engine Enforcement**: Security that lives exclusively in an external proxy can be circumvented if a compromised agent connects directly to the database. SolDefense integrates a native Lua preprocessor *inside* the Exasol engine itself. This creates a foolproof backstop—if the proxy is bypassed, the database itself refuses the connection.
3. **Native Runaway Agent Protection**: Traditional rate limits operate at the network layer, which is blind to database load, or require expensive external log processing. SolDefense uses a native Python UDF for windowed aggregation directly over the query audit log. It natively detects looping or flooding AI agents and suspends them before they can degrade performance for the entire connection pool.
