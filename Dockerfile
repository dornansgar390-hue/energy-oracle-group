FROM python:3.10-slim
RUN pip install --no-cache-dir requests eth-abi gridstatus pandas
WORKDIR /appCOPY enclave_oracle.py /app/enclave_oracle.py
ENTRYPOINT ["python", "/app/enclave_oracle.py"]