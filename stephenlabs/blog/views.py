from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import Http404
from .models import Post
from .forms import PostForm


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()
            return redirect('post_detail', slug=post.slug)
    else:
        form = PostForm()

    context = {
        'form': form,
        'title': 'Create New Article · StephenLabs'
    }
    return render(request, 'pages/post_form.html', context)


def post_list(request):
    posts = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author').prefetch_related('tags')

    context = {
        'posts': posts,
        'title': 'Insights & Articles · StephenLabs'
    }
    return render(request, 'pages/post_list.html', context)


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)

    # Draft protection
    if post.status == Post.Status.DRAFT:
        if not request.user.is_authenticated or post.author != request.user:
            raise Http404()

    context = {
        'post': post,
        'title': post.title
    }
    return render(request, 'pages/post_detail.html', context)


@login_required
def post_edit(request, slug):
    post = get_object_or_404(Post, slug=slug)

    if post.author != request.user:
        raise Http404('You are not allowed to edit this post')
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('post_detail', slug=post.slug)
        
    else:
        form = PostForm(instance=post)

    context = {
        'form': form,
        'title': f'Edit: {post.title} · StephenLabs'
    }
    return render(request, 'pages/post_form.html', context)


@login_required
def my_drafts(request):
    posts = Post.objects.filter(
        author=request.user,
        status=Post.Status.DRAFT
    ).order_by('-updated_at')

    context = {
        'posts': posts,
        'title': 'My Drafts · StephenLabs'
    }
    return render(request, 'pages/my_drafts.html', context)