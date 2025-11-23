from django.views.generic import ListView, DetailView

from .models import Post


class PostListView(ListView):
    queryset = Post.objects.filter(status="published")
    template_name = "blog/post_list.html"
    context_object_name = "posts"


class PostDetailView(DetailView):
    model = Post
    template_name = "blog/post_detail.html"
    slug_field = "slug"
    slug_url_kwarg = "slug"
    queryset = Post.objects.filter(status="published")
