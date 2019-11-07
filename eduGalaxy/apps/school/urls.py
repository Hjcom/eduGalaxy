from django.urls import path
from apps.school import views as school_view


app_name = 'school'

urlpatterns = [
    path('', school_view.index, name='index'),
    path('post/', school_view.AdminPostList.as_view(), name='post_list'),
    path('post/<int:pk>/', school_view.post_detail, name='post_detail'),
    path('post/review/<int:pk>/', school_view.review_list, name='review_list')
]

