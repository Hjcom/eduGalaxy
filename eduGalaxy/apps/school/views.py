from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic.base import TemplateView

from apps.school.models import Post, Review


##############
# index page #
##############
def index(request):
    return render(request, 'school/index.html')


###############
# school list #
###############
class AdminPostList(TemplateView):
    template_name = 'school/post_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['posts'] = Post.objects.all().order_by('-created_date')[:10]
        return context


#################
# school detail #
#################
def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    review_simple_list = Review.objects.filter(post_id=pk).order_by('-created_date')[:5]

    return render(request, 'school/base_detail.html', {'post': post,
                                                       'review_simple_list': review_simple_list})


###############
# review list #
###############
def review_list(request, pk):

    return render(request, 'school/review_list.html')

