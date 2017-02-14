#!/bin/bash
./cassandra_drop_keyspace.sh
./cassandra_create_keyspace.sh
./influxdb_drop_database.sh
./influxdb_create_database.sh
