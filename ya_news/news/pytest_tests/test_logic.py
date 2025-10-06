from http import HTTPStatus
from datetime import datetime, timedelta

from django.urls import reverse

import pytest

from pytest_django.asserts import assertRedirects

from conftest import TEXT_COMMENT
from news.forms import BAD_WORDS, WARNING
from news.models import Comment


@pytest.mark.django_db
def test_anonymous_user_cant_create_comment(client, news):
    """Анонимный пользователь не может отправить комментарий."""
    url = reverse('news:detail', args=(news.id,))
    initial_comment_count = Comment.objects.count()
    client.post(url, data={'text': 'Новый комментарий'})
    assert Comment.objects.count() == initial_comment_count


def test_user_can_create_comment(author_client, author, news):
    """Авторизованный пользователь может отправить комментарий."""
    url = reverse('news:detail', args=(news.id,))
    initial_comment_count = Comment.objects.count()
    new_comment_data = {'text': 'Новый комментарий'}
    author_client.post(url, data=new_comment_data)

    assert Comment.objects.count() == initial_comment_count + 1
    comment = Comment.objects.latest('id')
    assert comment.text == new_comment_data['text']
    assert comment.news == news
    assert comment.author == author


@pytest.mark.parametrize('bad_word', BAD_WORDS)
def test_user_cant_use_bad_words(author_client, news, bad_word):
    """Если комментарий содержит запрещённые слова, он не будет
    опубликован, а форма вернёт ошибку.
    """
    bad_words_data = {'text': f'Какой-то текст, {bad_word}, еще текст'}
    url = reverse('news:detail', args=(news.id,))
    initial_comment_count = Comment.objects.count()
    response = author_client.post(url, data=bad_words_data)

    assert Comment.objects.count() == initial_comment_count

    assert 'form' in response.context
    form = response.context['form']
    assert form.errors
    assert 'text' in form.errors
    assert WARNING in form.errors['text']


def test_author_can_delete_comment(author_client, news, comment):
    """Авторизованный пользователь может удалять свои комментарии."""
    news_url = reverse('news:detail', args=(news.id,))
    url_to_comments = reverse('news:delete', args=(comment.id,))
    initial_comment_count = Comment.objects.count()

    response = author_client.delete(url_to_comments)

    assertRedirects(response, news_url + '#comments')
    assert Comment.objects.count() == initial_comment_count - 1
    assert not Comment.objects.filter(id=comment.id).exists()


def test_user_cant_delete_comment_of_another_user(admin_client, comment):
    """Авторизованный пользователь не может удалять чужие комментарии."""
    comment_url = reverse('news:delete', args=(comment.id,))
    initial_comment_count = Comment.objects.count()

    response = admin_client.delete(comment_url)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Comment.objects.count() == initial_comment_count
    assert Comment.objects.filter(id=comment.id).exists()


def test_author_can_edit_comment(author_client, news, comment):
    """Авторизованный пользователь может редактировать свои комментарии."""
    news_url = reverse('news:detail', args=(news.id,))
    comment_url = reverse('news:edit', args=(comment.id,))
    new_text = 'Обновленный текст комментария'
    initial_comment_count = Comment.objects.count()

    response = author_client.post(comment_url, data={'text': new_text})

    assertRedirects(response, news_url + '#comments')
    assert Comment.objects.count() == initial_comment_count
    comment.refresh_from_db()
    assert comment.text == new_text
    assert comment.news == news
    assert comment.author == comment.author


def test_user_cant_edit_comment_of_another_user(admin_client, comment):
    """Авторизованный пользователь не может редактировать чужие комментарии."""
    comment_url = reverse('news:edit', args=(comment.id,))
    original_text = comment.text
    original_news = comment.news
    original_author = comment.author
    initial_comment_count = Comment.objects.count()

    response = admin_client.post(comment_url, data={'text': 'Новый текст'})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert Comment.objects.count() == initial_comment_count
    comment.refresh_from_db()
    assert comment.text == original_text
    assert comment.news == original_news
    assert comment.author == original_author
