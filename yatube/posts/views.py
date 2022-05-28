from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .models import Group, Post, User, Follow
from .forms import PostForm
from .forms import CommentForm
COUNT_POSTS = 10


def index(request):
    post_list = Post.objects.select_related('group', 'author').all()
    paginator = Paginator(post_list, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)

def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.select_related('author').all()
    paginator = Paginator(post_list, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)

def profile(request, username):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.select_related('author').all()
    paginator = Paginator(post_list, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user,
        author=author,
    ).exists()
    context = {
        'page_obj': page_obj,
        'author': author,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)

def post_detail(request, post_id):
    post_number = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    comments = post_number.comments.all()
    context = {
        'post_number': post_number,
        'comments': comments,
        'form': form,
    }
    return render(request, 'posts/post_detail.html', context)

@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)

@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect('posts:profile', username=request.user)
    else:
        context = {'form': form}
        return render(request, 'posts/create_post.html', context)

@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)
    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)

def follow_index(request):
    user = request.user
    post_list = Post.objects.filter(author__following__user=user)
    paginator = Paginator(post_list, COUNT_POSTS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj
    }
    return render(request, 'posts/follow.html', context)

@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    user = request.user
    if request.user != author:
        Follow.objects.get_or_create(user=user, author=author)
    return redirect('posts:profile', username=username)

@login_required
def profile_unfollow(request, username):
    user = get_object_or_404(User, username=request.user)
    author = get_object_or_404(User, username=username)
    if user != author:
        Follow.objects.filter(user=user, author=author).delete()
    return redirect('posts:profile', username=username)
