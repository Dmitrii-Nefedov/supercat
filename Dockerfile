FROM nginx:alpine AS web
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html sw.js manifest.json 404.html icon-192.png icon-512.png /usr/share/nginx/html/
COPY frontend/ /usr/share/nginx/html/frontend/
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

FROM python:3.12-slim AS cli
WORKDIR /app
COPY weather.py pyproject.toml README.md /app/
RUN pip install --no-cache-dir -e .
ENTRYPOINT ["supercat-weather"]
CMD ["--help"]
