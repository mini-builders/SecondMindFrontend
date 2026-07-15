from app.models.notification import NotificationDocument
from app.models.task import TaskDocument


class ParseResponse(TaskDocument):
    notification: NotificationDocument
