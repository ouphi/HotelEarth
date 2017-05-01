#!/bin/bash
SPARK_HOME=/home/ouphi/spark-2.0.2-bin-hadoop2.7
$SPARK_HOME/bin/spark-submit --master local[128] --driver-class-path=elasticsearch-hadoop-5.2.1/dist/elasticsearch-hadoop-5.2.1.jar --packages TargetHolding/pyspark-elastic:0.4.2 --conf spark.es.nodes=KxNOnP4 parser.py --dry-run