FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.9.16-slim-bullseye

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install -y openjdk-11-jre-headless && \
    apt-get clean;
    
COPY requirements.txt ./
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD [ "python", "./main.py" ]