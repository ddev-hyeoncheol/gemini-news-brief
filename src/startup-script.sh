#!/bin/bash

apt-get update

apt-get install -y python3-pip python3-venv git

mkdir -p /opt/gemini-news-brief
chmod 777 /opt/gemini-news-brief

echo "Gemini-News-Brief environment setup finished at: $(date)" >> /var/log/startup-script.log
