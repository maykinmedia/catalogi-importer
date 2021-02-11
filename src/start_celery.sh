#!/bin/sh

. ../env/bin/activate

# TODO add monitoring, beat, concurrency
exec celery -A importer worker -l info -o fair
