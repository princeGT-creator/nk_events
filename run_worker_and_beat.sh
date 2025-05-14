#!/bin/bash

# Kill old celerybeat schedule (optional but helps with cleanup)
rm -f celerybeat-schedule

gnome-terminal -- bash -c "celery -A celery_app worker --loglevel=info"
gnome-terminal -- bash -c "celery -A celery_app beat --loglevel=info"