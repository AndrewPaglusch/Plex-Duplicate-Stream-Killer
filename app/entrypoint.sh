#!/usr/bin/env ash

envsubst < /app/config.ini.TEMPLATE > /app/config.ini

python /app/run.py
