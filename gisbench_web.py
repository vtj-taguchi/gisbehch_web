import psycopg2
import json
from flask import Flask, request, render_template

import psutil
import subprocess
import threading

app = Flask(__name__, static_folder='.', static_url_path='')
usage_data = []

def make_usage_data():
  global usage_data
  n = 20
  t = []
  cpu_usage = []
  cpu_maxcore = []
  gpu_usage = []
  usage_data = [t, cpu_usage, cpu_maxcore, gpu_usage]
  nv_cmdline = ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits']

  # 配列の初期化
  for i in range(n):
    t.append(i - n + 1)
    cpu_usage.append(0)
    cpu_maxcore.append(0)
    gpu_usage.append(0)

  # データの更新
  while True:
    p = psutil.cpu_percent(interval=1, percpu=True)
    ca = int(sum(p) / len(p))
    cx = int(max(p))
    g = int(subprocess.run(nv_cmdline, capture_output=True, text=True).stdout)

    del cpu_usage[0]
    cpu_usage.append(ca)
    del cpu_maxcore[0]
    cpu_maxcore.append(cx)
    del gpu_usage[0]
    gpu_usage.append(g)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test')
def test():
    return render_template('index-test.html')

@app.route('/usage')
def usage():
  global usage_data
  return(json.dumps(usage_data))

@app.route('/search', methods=["GET"])
def search():
  req = request.args
  pgflag = req.get("pg_strom")
  dbname = "gis_bench"
  area_str = "" 
  whole_flag = False 
  AllJapan_flag = False

  if "全域" in req.get("q"):
    print("全域")
    whole_flag = True
    if req.get("q") == "日本全域":
      AllJapan_flag = True
    else:
      area_str = req.get("q").replace("全域", "")
  else:
    area_str = req.get("q") + '%'

  if req.get("gist") == "yes":
    tblname = "japan_cities"
  else:
    tblname = "japan_cities_no_idx"

  connector = psycopg2.connect('postgresql://{user}:{password}@{host}:{port}/{dbname}'.format( 
    user = "postgres",
    password = "",
    host = "localhost",
    port = "5432",
    dbname = dbname))

  cur = connector.cursor()
  if whole_flag:
    sql = 'SELECT n03_001 || n03_004, COUNT(n03_004) '\
      'FROM ' + tblname  + ' j, geopoint p '\
      'WHERE ST_Contains(j.geom, ST_SetSRID(ST_MakePoint(x,y), 4326)) '
    if not AllJapan_flag: sql += 'AND n03_001 LIKE \'' + area_str + '\' '
    sql += 'GROUP BY n03_001, n03_004 ORDER BY COUNT(n03_004) DESC'
    if AllJapan_flag: sql += ' LIMIT 100'
  else:
    sql = 'SELECT p.gid, p.x, p.y '\
      'FROM ' + tblname  + ' j, geopoint p '\
      'WHERE ST_Contains(j.geom, ST_SetSRID(ST_MakePoint(x,y), 4326)) '\
      'AND j.n03_004 like \'' + area_str + '\''

  if pgflag == "off":
    cur.execute('SET pg_strom.enabled = off')
    cur.execute('SET max_parallel_workers_per_gather = 96')
    cur.execute('SET parallel_setup_cost = 0')
    cur.execute('SET parallel_tuple_cost = 0')
  cur.execute(sql)
  result = cur.fetchall()
  return(json.dumps(result))

graph_thread = threading.Thread(target=make_usage_data)
graph_thread.setDaemon(True)
graph_thread.start()

#app.run(host='0.0.0.0', port=8080, debug=True)
app.run(host='0.0.0.0', port=8080, debug=False)
