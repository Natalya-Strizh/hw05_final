import shutil
import random
import tempfile
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import ImageFieldFile
from django.core.cache import cache

from posts.forms import PostForm

from ..models import Group, Post, Comment

User = get_user_model()


class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group
        )

    def setUp(self):
        # Создаём неавторизованный клиент
        self.guest_client = Client()
        # Создаём авторизованный клиент
        self.user = PostViewsTest.user
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cache.clear()
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_update', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def additional_function(self, response, obj):
        """Вспомогательная функция"""
        if obj == 'page_obj':
            post = response.context.get(obj).object_list[0]
        else:
            post = response.context.get('post_number')
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.group, self.post.group)

    def test_index_page_has_correct_context(self):
        """Проверяем что index передаёт правильный контекст"""
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        self.additional_function(response, 'page_obj')

    def test_group_post_has_correct_context(self):
        """Проверяем что group_post передаёт правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        group = response.context.get('group')
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.description, self.group.description)
        self.assertEqual(group.slug, self.group.slug)
        self.additional_function(response, 'page_obj')

    def test_profile_page_has_correct_context(self):
        """Проверяем что profile передаёт правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        author = response.context.get('author')
        self.assertEqual(author.username, self.user.username)

    def test_post_detail_page_has_correct_context(self):
        """Проверяем что post_detail передаёт правильный контекст"""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        self.additional_function(response, 'post_number')

    def test_post_create_page_has_correct_context(self):
        """Проверяем что create передаёт правильный контекст"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        self.assertIsInstance(response.context.get('form'), PostForm)

    def test_post_edit_page_has_correct_context(self):
        """Проверяем что post_edit передаёт правильный контекст"""
        post = self.post
        response = self.authorized_client.get(
            reverse('posts:post_update', kwargs={'post_id': self.post.id}))
        self.assertIsInstance(response.context.get('form'), PostForm)
        self.assertEqual(response.context.get('post'), post)
        self.assertTrue(response.context.get('is_edit'))

    def additional_check_when_creating_a_post(self):
        """Дополнительная проверка при создании поста. Пост появляется
        на главной странице, странице группы и профайле автора"""
        post = self.post
        dict = {
            reverse('posts:index'): Post.objects.all(),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            Post.objects.filter(group=post.group),
            reverse('posts:profile', kwargs={'username': self.user.username}):
            Post.objects.filter(author=post.author),
        }
        for reverse_name, filter in dict.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertTrue(filter.exists())

    def additional_check_when_creating_a_post(self):
        """Дополнительная проверка при создании поста. Пост не появляеться
        в другой группе"""
        post = self.post
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        self.assertNotIn(post, response.context.get('page_obj'))


LIMIT = 10


class PaginatorViewsTest(TestCase):
    """Класс с тестами пагинатора"""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовый текст',
            description='Тестовое описание',
            slug='test-slug',
        )
        cls.obj_pages = random.randint(1, LIMIT - 1)
        obj_posts = (Post(text='Текст №' + str(cls.obj_pages + 1),
                          author=cls.user,
                          group=cls.group
                          ) for i in range(LIMIT + cls.obj_pages))
        cls.post = Post.objects.bulk_create(obj_posts)
        cls.dict_url = {
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}),
            reverse('posts:profile', kwargs={'username': cls.user.username})
        }

    def setUp(self):
        # Создаём авторизованный клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.user)

    def test_first_page(self):
        for url in self.dict_url:
            response = self.authorized_client.get(url)
            self.assertEqual(len(response.context['page_obj']), LIMIT)

    def test_second_page(self):
        for url in self.dict_url:
            response = self.authorized_client.get(url, {'page': 2})
            self.assertEqual(len(response.context['page_obj']), self.obj_pages)


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CommentImages(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create(username='user')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_index_context(self):
        """Проверим вывод поста с картинкой index"""
        response = self.client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        image = first_object.image
        self.assertIsInstance(image, ImageFieldFile)

    def test_group_list_context(self):
        """Проверим вывод поста с картинкой group_list"""
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        image = first_object.image
        self.assertIsInstance(image, ImageFieldFile)

    def test_profile_context(self):
        """Проверим вывод поста с картинкой profile"""
        response = self.client.get(
            reverse('posts:profile', kwargs={'username': self.user.username}))
        first_object = response.context['page_obj'][0]
        image = first_object.image
        self.assertIsInstance(image, ImageFieldFile)

    def test_post_detail_context(self):
        """Проверим вывод поста с картинкой post_detail"""
        response = self.client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        post = response.context['post_number']
        image = post.image
        self.assertIsInstance(image, ImageFieldFile)

    def additional_check_when_creating_a_post(self):
        """После отправки комментарий появляется на странице поста"""
        self.authorized_client.get(
            f'/posts/{self.post.id}/comment/',
            follow=True
        )
        dict = {
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
            Comment.objects.all(),
        }
        for reverse_name, filter in dict.items():
            with self.subTest(reverse_name=reverse_name):
                self.assertTrue(filter.exists())

    def test_cache_index(self):
        """Проверка что кеш главной страницы работает"""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response_last = self.authorized_client.get(reverse('posts:index'))
        last_posts = response_last.content
        self.assertEqual(last_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(last_posts, new_posts)

    def follow_test_1(self):
        """проверяем отсутствиие подписок у пользователя"""
        count_follow = 0
        response = self.authorized_client.post(reverse('posts:follow_index'))
        self.assertEqual(len(response.context.get('paje_obj'), count_follow))

    def follow_test_2(self):
        """подписываем пользователя на автора и проверяем количество постов"""
        count_follow = 0
        self.authorized_client.post(
            reverse('posts:profile_follow', kwargs={'username': self.user.username}))
        response = self.authorized_client.post(reverse('posts:follow_index'))
        self.assertEqual(
            len(response.context.get('paje_obj'), count_follow + 1))

    def follow_test_3(self):
        """отписываем пользователя от автора и проверяем количество постов"""
        count_follow = 0
        self.authorized_client.post(
            reverse('posts:profile_unfollow',kwargs={'username': self.user.username}))
        response = self.authorized_client.post(reverse('posts:follow_index'))
        self.assertEqual(len(response.context.get('paje_obj'), count_follow))
