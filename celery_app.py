from celery import Celery
from celery.schedules import crontab

app = Celery(
    'fetch_customer',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Import your tasks to register them
from fetch_customer import scrape_customer_data_task
from fetch_payment_terms import scrape_customer_payment_terms
from final_invoice_auto import main

app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    # timezone='Europe/Rome',
    timezone='Asia/Kolkata',
    enable_utc=True,
    beat_schedule={
        'run-scrape-customer-data-task': {
            'task': 'scrape_customer_data_task',
            'schedule': crontab(hour=11, minute=22),  # Every day at 15:00
        },
        'run-scrape-payment-terms-task': {
            'task': 'scrape_customer_payment_terms',
            'schedule': crontab(hour=14, minute=13),
        },
        'run-scrape-payment-terms-task': {
            'task': 'final_invoice_auto',
            'schedule': crontab(hour=16, minute=50),
        },
    }
)
