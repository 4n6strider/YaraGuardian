from __future__ import absolute_import

import os

from celery import Celery
from django.conf import settings
from pythonjsonlogger import jsonlogger
from celery.signals import after_setup_task_logger, after_setup_logger

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'YaraGuardian.settings')

app = Celery('yara-guardian')

# Configure Database Backend
DATABASE_BACKEND = 'db+postgresql://{}:{}@{}:{}/{}'.format(settings.DB_USER,
                                                           settings.DB_PASS,
                                                           settings.DB_HOST,
                                                           settings.DB_PORT,
                                                           settings.DB_NAME)

# Configure Broker Backend
if settings.RMQ_PASS:
    BROKER_BACKEND = 'amqp://{}:{}@{}:{}/{}'.format(settings.RMQ_USER,
                                                   settings.RMQ_PASS,
                                                   settings.RMQ_HOST,
                                                   settings.RMQ_PORT,
                                                   settings.RMQ_VHOST)
else:
    BROKER_BACKEND = 'amqp://{}@{}:{}/{}'.format(settings.RMQ_USER,
                                                 settings.RMQ_HOST,
                                                 settings.RMQ_PORT,
                                                 settings.RMQ_VHOST)

# Autodiscover tasks from installed Django applications
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Update Celery instance with configurations
app.conf.update(
    broker_url = BROKER_BACKEND,
    result_backend = DATABASE_BACKEND,
    result_expires = 36000,  # 12 hours
    task_serializer = 'json',
    result_serializer = 'json'
)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))


@after_setup_task_logger.connect
@after_setup_logger.connect
def augment_celery_log(**args):
    JSON_formatter = jsonlogger.JsonFormatter('%(levelname)s %(asctime)s %(message)s')
    for handler in args['logger'].handlers:
        handler.setFormatter(JSON_formatter)
