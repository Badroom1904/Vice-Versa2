from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

import pytest

from news.models import News, Comment

TEXT_COMMENT = 'Текст комментария'
NEW_TEXT_COMMENT = 'Новый текст комментария'


@pytest.fixture
def author(django_user_model):
    """Создаём пользователя."""
    return django_user_model.objects.create(username='Автор')


@pytest.fixture
def author_client(author, client):
    """Создаём автора новости."""
    client.force_login(author)
    return client


@pytest.fixture
def news():
    """Создаём новость."""
    news = News.objects.create(
        title='Заголовок',
        text='Текст новости',
        date=datetime.today(),
    )
    return news


@pytest.fixture
def comment(news, author):
    """Создаём коммент."""
    comment = Comment.objects.create(
        text='Текст комментария',
        news=news,
        author=author
    )
    return comment


@pytest.fixture
def list_news():
    """Создаём список новостей."""
    today, list_news = datetime.today(), []
    for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1):
        news = News.objects.create(
            title=f'Новость {index}',
            text=f'Текст новости {index}',
        )
        news.date = today - timedelta(days=index)
        news.save()
        list_news.append(news)
    return list_news


@pytest.fixture
def list_comments(news, author):
    """Создаём список комментариев."""
    now, list_comment = timezone.now(), []
    for index in range(5):
        comment = Comment.objects.create(
            text=f'Текст комментария {index}',
            news=news,
            author=author,
        )
        comment.created = now + timedelta(days=index)
        comment.save()
        list_comment.append(comment)
    return list_comment
