# این ماژول در آینده برای پردازش ناهمگام (Asynchronous) با Celery یا Redis استفاده می‌شود.
# در حال حاضر، توابع این بخش مستقیماً در روترها صدا زده می‌شوند تا MVP سایت ساده بماند.

def enqueue_synthesis_task(user_id, files):
    pass

def enqueue_glfi_task(user_id, config):
    pass