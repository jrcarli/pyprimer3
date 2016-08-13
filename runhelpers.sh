#!/bin/bash

redis-server &
celery worker -A pyprimer3.celery --loglevel=info -f /tmp/celery.log &
