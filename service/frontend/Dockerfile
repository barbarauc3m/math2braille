FROM nginx:alpine
 
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ficheros estáticos del frontend (XHTML/CSS/JS)
COPY public/ /usr/share/nginx/html/

# Garantiza permisos de lectura y ejecución para todos los usuarios (no solo root), para que nginx pueda servirlos
RUN chmod -R o+rX /usr/share/nginx/html/

EXPOSE 80