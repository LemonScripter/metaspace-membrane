# MetaSpace.Bio privacy-first analytics — stdlib only, no third-party deps.
FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
# Railway sets $PORT; the DB lives on a mounted volume so counts survive redeploys.
ENV METASPACE_ANALYTICS_DB=/data/analytics.db
VOLUME ["/data"]
CMD ["python", "server.py"]
