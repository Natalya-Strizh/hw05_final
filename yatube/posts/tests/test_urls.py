from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post

User = get_user_model()
ACCEPTED = 200
FOUND = 302
NOT_FOUND = 404

class TaskURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая пост',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем пользователя
        self.user = TaskURLTests.user
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)

    def test_home(self):
        """Страница / доступна любому пользователю."""
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, ACCEPTED)

    def test_group(self):
        """Страница /group/test_slug/ доступна любому пользователю."""
        response = self.guest_client.get('/group/test_slug/')
        self.assertEqual(response.status_code, ACCEPTED)

    def test_posts(self):
        """Страница /posts/<int:post_id>/ доступна любому пользователю."""
        response = self.guest_client.get(f'/posts/{self.post.id}/')
        self.assertEqual(response.status_code, ACCEPTED)

    def test_profile(self):
        """Страница /profile/<str:username>/ доступна любому пользователю."""
        response = self.guest_client.get(f'/profile/{self.post.author}/')
        self.assertEqual(response.status_code, ACCEPTED)

    def test_unexisting_page(self):
        """Страница /unexisting_page/ доступна любому пользователю."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, NOT_FOUND)

    # Проверяем доступность страниц для авторизованного пользователя
    def test_create(self):
        """Страница '/create/' доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, ACCEPTED)

    def test_post_edit(self):
        """Страница '/posts/<int:post_id>/edit/'
        доступна авторизованному пользователю."""
        if self.authorized_client == self.post.author:
            response = self.authorized_client.get(
                f'/posts/{self.post.id}/edit/')
            self.assertEqual(response.status_code, ACCEPTED)

    # Проверяем редиректы для неавторизованного пользователя
    def test_create_url_redirect_anonymous(self):
        """Страница /create/перенаправляет анонимного пользователя."""
        response = self.guest_client.get('/create/')
        self.assertEqual(response.status_code, FOUND)

    def test_post_edit_url_redirect_anonymous(self):
        """Страница /posts/<int:post_id>/edit/ перенаправляет анонимного
        пользователя."""
        response = self.guest_client.get(f'/posts/{self.post.id}/edit/')
        self.assertEqual(response.status_code, FOUND)

    def test_urls_uses_correct_template1(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test_slug/': 'posts/group_list.html',
            '/profile/author/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)


    def test_add_comment_can_authorized_client(self):
        response = self.authorized_client.get(
            f'/posts/{self.post.id}/comment/',
            follow=True
        )
        self.assertEqual(response.status_code, ACCEPTED)

    def test_add_comment_cannot_guest_client(self):
        response = self.client.get(
            f'/posts/{self.post.id}/comment/',
        )
        self.assertEqual(response.status_code, FOUND)