FROM python AS builder

WORKDIR /usr/src/app

RUN python3 -m venv /venv
ENV PATH="/venv/bin:$PATH"

RUN apt-get update && apt-get install -y \
    cmake \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY /services/ml-processor .
RUN pip install --no-cache-dir .
RUN pip install -r extra_req.txt


FROM python AS test_runner
WORKDIR /tmp
COPY --from=builder /venv /venv
COPY --from=builder /usr/src/app/tests tests
ENV PATH=/venv/bin:$PATH

# install test dependencies
RUN pip install pytest

RUN mkdir -p /tmp/.mongodb && \
    wget "https://storage.yandexcloud.net/cloud-certs/CA.pem" \
    --output-document /tmp/.mongodb/root.crt && \
    chmod 0644 /tmp/.mongodb/root.crt

# run tests
RUN pytest tests


FROM python AS service
WORKDIR /root/app/site-packages
COPY --from=test_runner /tmp/.mongodb /root/app/site-packages/.mongodb
COPY --from=test_runner /venv /venv
COPY /services/ml-processor/src/endpoints/views/local_model/model_weights_v1.pth model_weights_v1.pth
ENV PATH=/venv/bin:$PATH