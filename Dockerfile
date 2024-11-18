FROM ubuntu:latest
RUN apt update
RUN apt install python3.10 python3-pip python3.10-dev -y
RUN apt install curl -y
COPY . ./app
WORKDIR ./app
RUN pip install -r requirements.txt
RUN rm docker-compose.yml
RUN rm -rf dbdata
RUN rm -rf .git .idea __pycache__
EXPOSE 3000
ENTRYPOINT ["python3","app.py"]
HEALTHCHECK --timeout=30s --retries=3 CMD curl -f http://localhost:3000/ || exit 1