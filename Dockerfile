FROM python:3.10-slim
RUN pip install --no-cache-dir requests eth-abi gridstatus pandas curl_cffi selectolax
WORKDIR /app
COPY enclave_oracle.py /app/enclave_oracle.py
COPY chaotic_defense.py /app/chaotic_defense.py
ENTRYPOINT ["python", "/app/enclave_oracle.py"]