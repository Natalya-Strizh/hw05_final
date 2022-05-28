from django.utils.translation import gettext_lazy as _
from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'text': _('Post_text'),
            'group': _('Post_group')
        }
        help_texts = {
            'text': _('Текст поста, обязательное для заполнения поле'),
            'group': _('Группа для поста, необязательное для заполнения поле')
        }


class CommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Comment
        fields = ('text',)
