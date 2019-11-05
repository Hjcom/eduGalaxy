from django.urls import path
from django.contrib.auth import views
from apps.user import views as user_views

app_name = 'user'

urlpatterns = [
    path('login/', views.LoginView.as_view(template_name='user/login.html'), name='login'),
    path('logout/', views.LogoutView.as_view(template_name='school/index.html'), name='logout'),
    path('agreement/', user_views.TemplateView.as_view(template_name='user/agreement.html'), name='signup'),
    path('signup/', user_views.EdUserCreateView.as_view(), name='eduser'),
    path('signup/<int:pk>/profile/', user_views.ProfileCreateView.as_view(), name='profile'),
    path('signup/<int:pk>/student/', user_views.StudentCreateView.as_view(), name='student'),

    path('signup/<int:pk>/parent/', user_views.ParentCreateView.as_view(), name='parent'),
    path('signup/<int:pk>/child/', user_views.TempChildCreateView.as_view(), name='add_temp_child'),
    path('signup/<int:pk>/child_delete/', user_views.TempChildDeleteView.as_view(), name='delete_temp_child'),
    path('signup/<int:pk>/school_auth/', user_views.SchoolAuthCreateView.as_view(), name='school_auth'),
    path('signup/<int:pk>/result/', user_views.ResultCreateView.as_view(), name='result'),
    path('signup/<int:pk>/delete', user_views.TempDeleteView.as_view(), name='temp_delete'),

    path('mypage/', user_views.EdUserMypageView.as_view(), name='mypage'),
    path('mypage/change_password/', user_views.PasswordChangeView.as_view(), name='change_password'),
    path('mypage/update_profile/', user_views.ProfileUpdateView.as_view(), name='update_profile'),
    path('mypage/update_student/', user_views.StudentUpdateView.as_view(), name='update_student'),
    path('mypage/update_school_auth/', user_views.SchoolAuthUpdateView.as_view(), name='update_school_auth'),

    path('mypage/update_parent/', user_views.ParentUpdateView.as_view(), name='update_parent'),
    path('mypage/add_child/', user_views.ChildAddView.as_view(), name='add_child'),
    path('mypage/detele_child/<int:pk>/', user_views.ChildDeleteView.as_view(), name='delete_child'),
    path('mypage/update_child/<int:pk>/', user_views.ChildUpdateView.as_view(), name='update_child'),

    # update child와 이어진 url
    path('mypage/create_child_edulevel/<int:pk>/', user_views.ChildEduLevelCreateView.as_view(), name='create_child_edulevel'),
    path('mypage/update_child_edulevel/<int:pk>/', user_views.ChildEduLevelUpdateView.as_view(), name='update_child_edulevel'),
    path('mypage/delete_child_edulevel/<int:pk>/', user_views.ChildEdulevelDeleteView.as_view(), name='delete_child_edulevel'),

    path('mypage/<int:pk>/update_edulevel/', user_views.EduLevelUpdateView.as_view(), name='update_edulevel'),
    path('mypage/<int:pk>/delete/', user_views.EdUserDeleteView.as_view(), name='user_delete'),

    path('<pk>/verify/<token>/', user_views.EduUserVerificationView.as_view(), name='verify'),
    path('resend_verify_email/', user_views.ResendVerificationEmailView.as_view(), name='resend'),
    path('login/social/<provider>/callback/', user_views.SocialLoginCallbackView.as_view(), name='social_callback'),
]

