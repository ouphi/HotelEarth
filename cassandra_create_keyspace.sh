#!/bin/sh
query="CREATE KEYSPACE hotel_earth WITH replication = {'class':'SimpleStrategy', 'replication_factor' : 1};
CREATE TABLE hotel_earth.booking (
       country text,
       city text,
       name text,
       url text,
       latitude double,
       longitude double,
       rate float,
       address text,
       pictures list<text>,
       PRIMARY KEY ((country, city), name)
);
"
echo $query | cqlsh
