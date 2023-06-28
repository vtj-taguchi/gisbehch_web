# PG-Strom デモアプリ gisbench_web セットアップ手順

## このデモアプリについて

日本全域（北緯20.0～46.2度、東経123.0～154.2度内）に1000万件のダミーPOIを作成し、指定した区域にどれだけ散らばっているかを集計します。このデモアプリを使うことでPG-Stromの次の特徴を体験することができます。

- PG-StromによるGPUを使った並列処理による処理の高速化
- PG-StromとGiSTインデックスを組み合わせた位置情報検索の高速化

## 用意するもの

- デモアプリ本体 (gisbench_web)
- 国土数値情報 行政区域データ 全国版

## 前提条件

- 以下のパッケージ／モジュールをインストールしておきます（以下のセットアップ手順は省略します）
  - Python3
  - PostgreSQL
  - PG-Strom
  - PostGIS
  - PostGIS-client

## 動作環境

このプログラムは以下の環境で動作することこを確認しています。

- Red Hat Enterprise Linux 8.6
- PostgreSQL 13 および 15
- PG-Strom 3.x
- PostGIS 3.2.5
- Python 3.9


## ファイルのダウンロード

### デモアプリ本体

```bash
$ git clone https://github.com/vtj-taguchi/gisbehch_web.git
```

### 国土数値情報

国土交通省の国土数値情報ダウンロードサイトへアクセスし、国土数値情報行政区域データ（全国版）をダウンロードしてください（約400MB）。

- https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-v2_3.html

## セットアップ

### デモアプリで使用するPythonライブラリのインストール

```bash
$ python3 -m pip install psycopg2 flask psutil matplotlib
```

### データベースの作成

```bash
$ psql -U postgres -d postgres
```

```SQL
-- DBの作成
CREATE DATABASE gis_bench;

-- 作成したDB gis_bench への切り替え
\c gis_bench

-- 拡張機能の有効化
CREATE EXTENSION pg_strom;
CREATE EXTENSION postgis;
```

### 国土数値情報の圧縮ファイル展開

```bash
$ mkdir gsidata
$ unzip N03-190101_GML.zip -d gsidata
```

### 国土数値情報のシェープファイルをPostgreSQLダンプへ変換

```bash
$ shp2pgsql -s 4612 -D -i -W cp932 gsidata/N03-19_190101.shp japan_cities > japan_cities_tbl.sql
```

### 行政区域データのインポート

```bash
$ psql -U postgres -d gis_bench -f japan_cities_tbl.sql
```

### 行政区域データテーブルのインデックス作成とインデックスなしテーブルの作成

```bash
$ psql -U postgres -d gis_bench
```

```SQL
-- GiSTインデックスの作成
CREATE INDEX ON japan_cities USING gist (geom);

-- GiSTインデックスなしテーブルの作成
CREATE TABLE japan_cities_no_idx AS SELECT * FROM japan_cities;
```

### 位置情報ランダムデータの作成

```SQL
-- ランダムデータ用テーブルの作成
CREATE TABLE geopoint (gid int primary key, x float8, y float8);

-- ランダムデータ1000万件の生成
INSERT INTO geopoint (SELECT x, pgstrom.random_float(0, 123.0, 154.2),
  pgstrom.random_float(0, 20.0, 46.2)
  FROM generate_series(1,10000000) x);
```

### ファイヤーウォールのポート開放

必要に応じてデモアプリで使用するポートを開放します。

```
$ firewall-cmd --permanent --add-port=8080/tcp
$ firewall-cmd --reload
```

## Webアプリの起動

以下のコマンドでアプリ起動後、Webブラウザより ```http://[サーバーのIPアドレス]:8080/``` へアクセスします。

```bash
$ python3 gisbench_web/gisbench_web.py
```

## デモアプリのsystemd登録（必要に応じて）

デモアプリを自動起動させたい場合は、以下の手順でsystemdへ登録します。

### pythonプログラムのコピー

```bash
$ sudo cp gisbench_web/gisbench_web.service /etc/systemd/system
$ sudo cp gisbench_web /opt
```

### systemdユニットファイルのユーザー指定

```/etc/systemd/system/gisbench_web.service``` を開き、```User``` 行で実行するユーザーを指定します。

```
[Unit]
Description = GIS Bench Web
Requires=network-online.target
Wants=network-online.target
After=network-online.target

[Service]
ExecStart = /usr/bin/python3 /opt/gisbench_web/gisbench_web.py
Restart = always
User = cloud-user    # ← 環境に応じて変更
Type = simple

[Install]
WantedBy = multi-user.target
```

### systemdの再読込

```bash
$ sudo systemctl daemon-reload
```

### デモアプリのサービス有効化と起動

```bash
$ sudo systemctl enable gisbench_web
$ sudo systemctl start gisbench_web
```
