# w

A basic FastAPI app that apply simple transformation on base64 images and returns base64 encoded image with logging possible errors and process steps


To be able to run this project:
```
$ git clone https://github.com/mahirk27/w
$ cd w
```

```
$ docker build -t my-fastapi-app .
$ docker run -d -p 8080:80 --name fastapi my-fastapi-app
$ docker logs -f fastapi
```
Also created app.log file can be seen with commands below
```
$ docker exec -it fastapi /bin/sh
$ cd /tmp/logs
$ cat app.log
```
