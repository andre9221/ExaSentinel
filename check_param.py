import pyexasol, ssl
conn = pyexasol.connect(dsn='localhost:8563', user='sys', password='exasol', websocket_sslopt={'cert_reqs': ssl.CERT_NONE})
for r in conn.execute("SELECT * FROM EXA_PARAMETERS WHERE PARAMETER_NAME = 'SQL_PREPROCESSOR_SCRIPT'").fetchall(): print(r)
