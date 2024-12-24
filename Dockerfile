FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.9.16-slim-bullseye

WORKDIR /usr/src/app

RUN sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g' /etc/apt/sources.list

RUN set -eux; apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    apt-get clean;

COPY requirements.txt ./
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8080

CMD [ "/usr/local/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080" ]