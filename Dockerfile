FROM python:3.13-slim@sha256:2d44738ebf4ce5f63b9d9ea871e9c7cfdc0426f7b0c97cac915fd88ded1d86bb

WORKDIR /app
COPY requirements.txt ./

RUN python -m pip install --no-cache-dir -r requirements.txt
COPY src ./src
RUN useradd --uid 10001 --create-home skyland && mkdir -p logs && chown -R skyland:skyland /app

ENV TZ=Asia/Shanghai

ENV TOKEN=""
ENV SC3_SENDKEY=""
ENV SC3_UID=""
USER skyland

CMD ["python", "src/main.py" ]
