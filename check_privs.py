import pyexasol, ssl
conn = pyexasol.connect(dsn='localhost:8563', user='sys', password='exasol', websocket_sslopt={'cert_reqs': ssl.CERT_NONE})
print("OBJ PRIVS:")
for r in conn.execute("SELECT * FROM EXA_DBA_OBJ_PRIVS WHERE GRANTEE='AI_AGENT'").fetchall(): print(r)
print("SYS PRIVS:")
for r in conn.execute("SELECT * FROM EXA_DBA_SYS_PRIVS WHERE GRANTEE='AI_AGENT'").fetchall(): print(r)
