FROM minio/mc:latest

COPY init-minio.sh /usr/bin/init-minio.sh
RUN chmod +x /usr/bin/init-minio.sh

ENTRYPOINT ["/usr/bin/init-minio.sh"]
