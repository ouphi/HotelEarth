#!/bin/bash
SPARK_HOME=/home/ouphi/spark-2.0.2-bin-hadoop2.7
$SPARK_HOME/bin/spark-submit --master local[128] --packages com.datastax.spark:spark-cassandra-connector_2.11:2.0.0-M3 parser.py
