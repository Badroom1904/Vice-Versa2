from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from pytils.translit import slugify

from notes.models import Note
from notes.forms import WARNING

User = get_user_model()


class TestLogic(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create(username='author')
        cls.author_client = Client()
        cls.author_client.force_login(cls.author)
        cls.auth_user = User.objects.create(username='auth_user')
        cls.auth_user_client = Client()
        cls.auth_user_client.force_login(cls.auth_user)
        cls.data = {
            'title': 'Новый заголовок',
            'text': 'Новый текст',
            'slug': 'new-slug'
        }
        # Создаем тестовую заметку один раз для всех тестов
        cls.existing_note = Note.objects.create(
            title='Существующая заметка',
            text='Текст существующей заметки',
            author=cls.author,
            slug='existing-slug'
        )

    def test_user_can_create_note(self):
        """Залогиненный пользователь может создать заметку."""
        url = reverse('notes:add')
        response = self.author_client.post(url, data=self.data)
        self.assertRedirects(response, reverse('notes:success'))
        # Должно быть 2 заметки: одна из setUpTestData + новая
        self.assertEqual(Note.objects.count(), 2)
        new_note = Note.objects.get(slug=self.data['slug'])
        self.assertEqual(new_note.title, self.data['title'])
        self.assertEqual(new_note.text, self.data['text'])
        self.assertEqual(new_note.slug, self.data['slug'])
        self.assertEqual(new_note.author, self.author)

    def test_anonymous_user_cant_create_note(self):
        """Анонимный пользователь не может создать заметку."""
        url = reverse('notes:add')
        response = self.client.post(url, self.data)
        login_url = reverse('users:login')
        expected_url = f'{login_url}?next={url}'
        self.assertRedirects(response, expected_url)
        # Должна остаться только заметка из setUpTestData
        self.assertEqual(Note.objects.count(), 1)

    def test_not_unique_slug(self):
        """Невозможно создать две заметки с одинаковым slug."""
        url = reverse('notes:add')
        response = self.author_client.post(url, data={
            'title': 'Новый заголовок',
            'text': 'Новый текст',
            'slug': self.existing_note.slug
        })

        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertIn('form', response.context)

        form = response.context['form']
        self.assertTrue(form.errors)

        self.assertIn('slug', form.errors)

        expected_error = self.existing_note.slug + WARNING
        self.assertIn(expected_error, form.errors['slug'])

        self.assertEqual(Note.objects.count(), 1)

    def test_empty_slug(self):
        """Если при создании заметки не заполнен slug, то он формируется
        автоматически, с помощью функции pytils.translit.slugify
        """
        url = reverse('notes:add')
        data_without_slug = self.data.copy()
        data_without_slug.pop('slug')
        response = self.author_client.post(url, data=data_without_slug)
        self.assertRedirects(response, reverse('notes:success'))
        # Должно быть 2 заметки
        self.assertEqual(Note.objects.count(), 2)
        new_note = Note.objects.get(slug=slugify(self.data['title']))
        expected_slug = slugify(self.data['title'])
        self.assertEqual(new_note.slug, expected_slug)

    def test_author_can_delete_note(self):
        """Пользователь может удалять свои заметки."""
        url = reverse('notes:delete', args=(self.existing_note.slug,))
        response = self.author_client.post(url)
        self.assertRedirects(response, reverse('notes:success'))
        self.assertEqual(Note.objects.count(), 0)

    def test_other_user_cant_delete_note(self):
        """Пользователь не может удалять чужие заметки."""
        url = reverse('notes:delete', args=(self.existing_note.slug,))
        response = self.auth_user_client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(Note.objects.count(), 1)

    def test_author_can_edit_note(self):
        """Пользователь может редактировать свои заметки."""
        url = reverse('notes:edit', args=(self.existing_note.slug,))
        response = self.author_client.post(url, self.data)
        self.assertRedirects(response, reverse('notes:success'))
        self.existing_note.refresh_from_db()
        self.assertEqual(self.existing_note.title, self.data['title'])
        self.assertEqual(self.existing_note.text, self.data['text'])
        self.assertEqual(self.existing_note.slug, self.data['slug'])

    def test_other_user_cant_edit_note(self):
        """Пользователь не может редактировать чужие заметки."""
        url = reverse('notes:edit', args=(self.existing_note.slug,))
        response = self.auth_user_client.post(url, self.data)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.existing_note.refresh_from_db()
        self.assertNotEqual(self.existing_note.title, self.data['title'])
        self.assertNotEqual(self.existing_note.text, self.data['text'])
        self.assertNotEqual(self.existing_note.slug, self.data['slug'])
