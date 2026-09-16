import pyexasol, ssl
conn = pyexasol.connect(dsn='localhost:8563', user='sys', password='exasol', websocket_sslopt={'cert_reqs': ssl.CERT_NONE})
for r in conn.execute("SELECT * FROM DEMO.QUERY_LOG WHERE AGENT_ID='runaway-agent'").fetchall(): print(r)
for r in conn.execute("SELECT * FROM DEMO.SUSPENDED_AGENTS").fetchall(): print(r)
