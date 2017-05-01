#!/bin/bash
./es_drop_index.sh
./influxdb_drop_database.sh
./influxdb_create_database.sh
