import pyexasol, ssl
conn = pyexasol.connect(dsn='localhost:8563', user='sys', password='exasol', websocket_sslopt={'cert_reqs': ssl.CERT_NONE})
try:
    print(conn.execute("SELECT DEMO.LOOP_DETECTOR(5, 5, agent_id, raw_sql) FROM (SELECT agent_id, raw_sql FROM DEMO.QUERY_LOG) GROUP BY agent_id").fetchall())
except Exception as e:
    print(e)
