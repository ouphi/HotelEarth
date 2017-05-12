# Hotel Earth
A fancy WebGL globe representing all hotels around the world. [https://hotel-earth.world](https://hotel-earth.world)

![Screenshot 1](http://i.imgur.com/BTbHXCk.jpg)
![Screenshot 2](http://i.imgur.com/BCWmfWq.png)
![Screenshot 3](http://i.imgur.com/7h7sDh4.jpg)

## Content
You will find in this repository the following:
1. A Spark job that crawls the booking.com website to extract all hotel information
2. Shell scripts to create/drop influxdb and ElasticSearch databases to log the job activity and store the hotel informations
3. The front-end code of the website
4. The Apache configuration for this website to use ElasticSearch directy as a back-end but in a secure way (Readonly)

## Picture of the influxdb logs
![Logs](http://i.imgur.com/kLdTqb7.png)
