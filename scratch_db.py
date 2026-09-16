import pyexasol
import ssl
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\an705\Documents\Andrea\vit\internship\projects\exasol\exas")

conn = pyexasol.connect(
    dsn="localhost:8563",
    user="sys",
    password="exasol",
    websocket_sslopt={"cert_reqs": ssl.CERT_NONE},
)

def run_query(q):
    q = q.strip()
    if not q: return
    print(f"Running: {q[:50]}...")
    try:
        conn.execute(q)
    except Exception as e:
        msg = str(e).lower()
        if any(x in msg for x in ("already exists", "not granted")): pass
        else: print(f"Error: {e}")

# 1. 08_loop_detector tables
run_query("CREATE TABLE IF NOT EXISTS DEMO.LOOP_QUERY_LOG (session_id DECIMAL(20, 0), user_name VARCHAR(128), query_text VARCHAR(2000), query_fingerprint VARCHAR(64), query_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
run_query("CREATE TABLE IF NOT EXISTS DEMO.SECURITY_CONFIG (config_key VARCHAR(64), config_value VARCHAR(64))")
run_query("INSERT INTO DEMO.SECURITY_CONFIG (config_key, config_value) SELECT 'max_queries_per_window', '5' WHERE NOT EXISTS (SELECT 1 FROM DEMO.SECURITY_CONFIG WHERE config_key = 'max_queries_per_window')")
run_query("INSERT INTO DEMO.SECURITY_CONFIG (config_key, config_value) SELECT 'window_minutes', '1' WHERE NOT EXISTS (SELECT 1 FROM DEMO.SECURITY_CONFIG WHERE config_key = 'window_minutes')")
run_query("CREATE TABLE IF NOT EXISTS DEMO.APPROVED_FINGERPRINTS (query_fingerprint VARCHAR(64), description VARCHAR(200))")
run_query("CREATE TABLE IF NOT EXISTS DEMO.FLAGGED_SESSIONS (session_id DECIMAL(20, 0), user_name VARCHAR(128), flagged_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, killed BOOLEAN DEFAULT FALSE)")

# 2. UDFs
fingerprint = """
CREATE OR REPLACE PYTHON3 SCALAR SCRIPT DEMO.FINGERPRINT_QUERY(query_text VARCHAR(2000)) RETURNS VARCHAR(64) AS
import re
import hashlib
def run(ctx):
    text = ctx.query_text
    if text is None: return None
    norm = re.sub(r'\s+', ' ', text.strip())
    norm = re.sub(r"'[^']*'", '?', norm)
    norm = re.sub(r'\b\d+\b', '?', norm)
    return hashlib.sha256(norm.lower().encode('utf-8')).hexdigest()[:16]
/
"""
run_query(fingerprint.strip().partition("\n/")[0])

kill_script = """
CREATE OR REPLACE LUA SCRIPT DEMO.KILL_FLAGGED_SESSIONS () AS
    local rows = query([[SELECT session_id FROM DEMO.FLAGGED_SESSIONS WHERE killed = FALSE]])
    for i = 1, #rows do
        local sid = rows[i][1]
        pcall(query, "KILL SESSION " .. sid)
        pcall(query, [[UPDATE DEMO.FLAGGED_SESSIONS SET killed = TRUE WHERE session_id = ]] .. sid)
    end
/
"""
run_query(kill_script.strip().partition("\n/")[0])

loop_udf = (ROOT / "udf" / "loop_detector_udf.sql").read_text(encoding="utf-8")
run_query(loop_udf.strip().partition("\n/")[0])

# 3. 06_lua_preprocessor
lua_prep = (ROOT / "sql" / "06_lua_preprocessor.sql").read_text(encoding="utf-8")
run_query(lua_prep.strip().partition("\n/")[0])

# 4. 07_proxy_grants
run_query("GRANT SELECT, INSERT ON DEMO.LOOP_QUERY_LOG TO PROXY_SERVICE_USER")
run_query("GRANT SELECT ON DEMO.SECURITY_CONFIG TO PROXY_SERVICE_USER")
run_query("GRANT SELECT ON DEMO.APPROVED_FINGERPRINTS TO PROXY_SERVICE_USER")
run_query("GRANT SELECT, INSERT ON DEMO.FLAGGED_SESSIONS TO PROXY_SERVICE_USER")
run_query("GRANT EXECUTE ON DEMO.FINGERPRINT_QUERY TO PROXY_SERVICE_USER")
run_query("GRANT EXECUTE ON DEMO.KILL_FLAGGED_SESSIONS TO PROXY_SERVICE_USER")
run_query("GRANT SELECT ON DEMO.LOOP_QUERY_LOG TO AI_AGENT_TEST")
run_query("GRANT SELECT ON DEMO.SECURITY_CONFIG TO AI_AGENT_TEST")
run_query("GRANT SELECT ON DEMO.APPROVED_FINGERPRINTS TO AI_AGENT_TEST")
run_query("GRANT SELECT ON DEMO.FLAGGED_SESSIONS TO AI_AGENT_TEST")
run_query("GRANT EXECUTE ON DEMO.FINGERPRINT_QUERY TO AI_AGENT_TEST")
run_query("GRANT INSERT, SELECT ON DEMO.QUERY_LOG TO PROXY_SERVICE_USER")
run_query("GRANT INSERT, SELECT ON DEMO.SUSPENDED_AGENTS TO PROXY_SERVICE_USER")
run_query("GRANT EXECUTE ON DEMO.SQL_GUARD TO PROXY_SERVICE_USER")
run_query("GRANT EXECUTE ON DEMO.LOOP_DETECTOR TO PROXY_SERVICE_USER")

# Enforce guards on users!
run_query("ALTER USER AI_AGENT_TEST SET SQL_PREPROCESSOR_SCRIPT = 'DEMO.SQL_GUARD'")
run_query("ALTER USER AI_AGENT SET SQL_PREPROCESSOR_SCRIPT = 'DEMO.SQL_GUARD'")
print("FINISHED FIXING DATABASE")