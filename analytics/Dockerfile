# MetaSpace.Bio privacy-first analytics — stdlib only, no third-party deps.
FROM python:3.12-slim
WORKDIR /app
COPY server.py /app/server.py
# Railway sets $PORT; the DB lives on a Railway Volume mounted at /data (attached to the
# service, not declared here — Railway rejects the Docker VOLUME instruction) so counts
# survive redeploys.
ENV METASPACE_ANALYTICS_DB=/data/analytics.db
CMD ["python", "server.py"]
