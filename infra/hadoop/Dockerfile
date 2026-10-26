FROM eclipse-temurin:17-jre-jammy
ARG HADOOP_VERSION=3.4.1
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates python3 && rm -rf /var/lib/apt/lists/*
RUN --mount=type=bind,source=cache,target=/tmp/hadoop-cache \
    if [ -f /tmp/hadoop-cache/hadoop.tgz ] && [ -f /tmp/hadoop-cache/hadoop.sha512 ]; then \
        cp /tmp/hadoop-cache/hadoop.tgz /tmp/hadoop.tgz && cp /tmp/hadoop-cache/hadoop.sha512 /tmp/hadoop.sha512; \
    else \
        curl -fSL "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" -o /tmp/hadoop.tgz \
        && curl -fSL "https://archive.apache.org/dist/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz.sha512" -o /tmp/hadoop.sha512; \
    fi \
    && python3 -c "import hashlib,re; expected=re.search(r'(?i)\b[0-9a-f]{128}\b',open('/tmp/hadoop.sha512').read()).group().lower(); digest=hashlib.sha512(); stream=open('/tmp/hadoop.tgz','rb'); [digest.update(chunk) for chunk in iter(lambda: stream.read(1048576), b'')]; assert digest.hexdigest() == expected, 'Hadoop checksum mismatch'" \
    && tar -xzf /tmp/hadoop.tgz -C /opt \
    && mv /opt/hadoop-${HADOOP_VERSION} /opt/hadoop \
    && rm /tmp/hadoop.tgz /tmp/hadoop.sha512
ENV HADOOP_HOME=/opt/hadoop
ENV PATH=/opt/hadoop/bin:$PATH
COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh
