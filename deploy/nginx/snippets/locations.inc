# Shared routing, included by the HTTP (local) and HTTPS (prod) servers.

location = /nginx-health {
    access_log off;
    default_type text/plain;
    return 200 "ok\n";
}

# Metrics are scraped on the internal network (api:8000/v1/metrics), never through the gateway.
location = /v1/metrics { return 404; }
location = /api/v1/metrics { return 404; }

# Public, anonymous endpoints: stricter per-IP limit (code enumeration, click floods).
location ~ ^/(api/)?(r|v1/r|v1/public)/ {
    limit_req zone=public burst=20 nodelay;
    rewrite ^/api/(.*)$ /$1 break;
    rewrite ^/r/(.*)$ /v1/r/$1 break;
    proxy_pass http://api;
    include /etc/nginx/snippets/proxy.inc;
}

location /api/v1/ {
    limit_req zone=api burst=100 nodelay;
    rewrite ^/api/(.*)$ /$1 break;
    proxy_pass http://api;
    include /etc/nginx/snippets/proxy.inc;
}

location /v1/ {
    limit_req zone=api burst=100 nodelay;
    proxy_pass http://api;
    include /etc/nginx/snippets/proxy.inc;
}

location / {
    return 404;
}
