# w


To be able to run this project:
```
$ docker build -t my-fastapi-app .
$ docker run -d -p 8080:80 --name fastapi my-fastapi-app
$ docker logs -f fastapi
```
Also created app.log file can be seen with 
```
$ docker exec -it fastapi /bin/sh
$ cd /tmp/logs
$ cat app.log
```
