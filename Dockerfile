# build ops/cfg
FROM golang:1.14 AS go-kit-build

RUN git clone --depth=1 --branch v1.0.20 https://github.com/hatlonely/go-kit.git go-kit && \
    cd go-kit && make build

# build helm
FROM golang:1.14 AS helm-build

RUN git clone --depth=1 --branch v3.5.4 https://github.com/helm/helm.git && \
    cd helm && make

FROM centos:centos8
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" >> /etc/timezone

# ops
COPY --from=go-kit-build /go/go-kit/build/bin /work/bin

# helm
COPY --from=helm-build /go/helm/bin /work/bin

# python3
RUN dnf module -y install python38 && pip3 install --upgrade pip

# wget/unzip/gcc/jq/git/make
RUN dnf install -y wget unzip gcc python38-devel jq crontabs git make

# aliyunlog
RUN pip3 install aliyun-log-python-sdk aliyun-log-cli -U --no-cache

# ossutil
RUN wget http://gosspublic.alicdn.com/ossutil/1.7.2/ossutil64 && chmod +x ossutil64 && mv ossutil64 /usr/local/bin/ossutil

# aliyun
RUN wget https://aliyuncli.alicdn.com/aliyun-cli-linux-3.0.32-amd64.tgz && \
    tar -xzvf aliyun-cli-linux-3.0.32-amd64.tgz && \
    mv aliyun /usr/local/bin/aliyun

COPY alics/requirements.txt /work/ops/alics/requirements.txt
RUN pip3 install -r /work/ops/alics/requirements.txt

# mnscmd
RUN wget https://aliware-images.oss-cn-hangzhou.aliyuncs.com/mns/sdk/python/aliyun-mns-python-sdk-1.1.5.zip && \
    unzip aliyun-mns-python-sdk-1.1.5.zip && \
    cd mns_python_sdk && python3 setup.py install && cd .. && rm -rf aliyun-mns-python-sdk-1.1.5.zip mns_python_sdk

# kubectl
RUN curl -L -o /work/bin/kubectl https://dl.k8s.io/release/v1.21.0/bin/linux/amd64/kubectl && chmod +x /work/bin/kubectl

# docker
RUN dnf install -y 'dnf-command(config-manager)' && \
    dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo && \
    dnf install -y docker-ce docker-ce-cli containerd.io

COPY alics /work/ops/alics
COPY tool /work/ops/tool
COPY entrypoint.sh /work/entrypoint.sh

ENTRYPOINT ["/work/entrypoint.sh"]

ENV OPS=/work/ops
ENV PATH=$PATH:/work/bin
WORKDIR /work

RUN helm plugin install https://github.com/databus23/helm-diff

CMD ["sh"]
