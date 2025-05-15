#!/usr/bin/env bash

set +x
set -e
sudo amazon-linux-extras enable python3.8
sudo yum install -y python3.8
python3.8 -m ensurepip --upgrade
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cat <<EOF2 > /etc/systemd/system/ec2parent.service
[Unit]
Description=Gunicorn instance for a simple flask app
After=network.target
[Service]
User=ec2-user
Group=www-data
WorkingDirectory=/home/ec2-user/PythonSockets
ExecStart=/home/ec2-user/PythonSockets/venv/bin/gunicorn -b localhost:5000 parent:app
Restart=always
[Install]
WantedBy=multi-user.target
EOF2

sudo yum install -y nginx
cat <<EOF2 > /etc/nginx/conf.d/default
upstream flask_app {
    server 127.0.0.1:5000;
}
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    
    return 301 https://\$host\$request_uri;
}
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    ssl_certificate cert.pem;
    ssl_certificate_key key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'HIGH:!aNULL:!MD5';
    

    root /var/www/html;
    index index.html index.htm index.nginx-debian.html;
    server_name _;

    location / {
        proxy_pass http://flask_app;
    }
}
EOF2
cat <<EOF2 > README
ATTENTION: If you started up this instance with terraform, you need to run the following commands to get the server up and running with a self-signed HTTPS:

openssl req -x509 -newkey rsa:2048 -nodes -keyout /etc/nginx/key.pem -out /etc/nginx/cert.pem -days 365
sudo systemctl daemon-reload
sudo systemctl start ec2parent
sudo systemctl enable ec2parent
sudo systemctl start nginx
sudo systemctl enable nginx

WARNING! Do not use this self-signed certificate in production. It is only for testing purposes.
You should use a proper certificate from a trusted CA.
You can use Let's Encrypt for free certificates.
You can use certbot to get a certificate from Let's Encrypt.
(Buying a domain is not free though, you have to pay for that)

LASTLY: You need to install docker to run the enclaves. Look up enclave docs for more info.
EOF2

sudo amazon-linux-extras enable docker
sudo yum install -y docker
sudo usermod -aG docker ec2-user
newgrp docker
sudo systemctl start docker
sudo systemctl enable docker
docker --version
echo -e "If all looks good, run the following commands to get docker in working order:\ndocker build -t test_enclave . \ndocker run -d --name test_enclave -p 12345:12345 test_enclave\n"