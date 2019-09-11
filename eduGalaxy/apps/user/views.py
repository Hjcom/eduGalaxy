from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.edit import FormView, View, UpdateView
from django.views.generic.base import TemplateView, RedirectView

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model, login
from django.contrib import messages
from django.utils import timezone

# social auth
from .oauth.providers.naver import NaverLoginMixin
from django.middleware.csrf import _compare_salted_tokens
from django.core.exceptions import ObjectDoesNotExist

from .mixins import VerificationEmailMixin
from apps.user.forms import EdUserCreationForm, ProfileCreationForm, StudentCreationForm, SchoolAuthCreationForm, PasswordChangeForm
from apps.user.forms import ProfileUpdateForm
from apps.user.models import EdUser, Temp, Profile, Student, SchoolAuth


# 회원가입
class EdUserCreateView(FormView):
    form_class = EdUserCreationForm
    template_name = 'user/create_user.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        temp = form.save(commit=False)
        temp.create_date = timezone.now()
        temp.save()
        eduser_id = temp.id
        return HttpResponseRedirect(reverse_lazy('user:profile', kwargs={'pk': eduser_id}))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class ProfileCreateView(FormView):
    form_class = ProfileCreationForm
    template_name = 'user/create_profile.html'

    def get_object(self):
        pk = self.kwargs['pk']
        return get_object_or_404(Temp, id=pk)

    def get(self, request, *args, **kwargs):
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        temp = self.get_object()
        if 'next' in self.request.POST:
            data = form.profile_data()
            group = self.request.POST['group']
            pk = temp.id

            if group == "학생":
                nexturl = 'user:student'
            elif group == "학교 관계자":
                nexturl = 'user:school_auth'
            else:
                return render(self.request, self.template_name, {
                    'error_message': "직업을 선택해주세요",
                })
            temp.profile = data
            temp.create_date = timezone.now()
            temp.save()

            return HttpResponseRedirect(reverse_lazy(nexturl, kwargs={'pk': pk}))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class StudentCreateView(FormView):
    form_class = StudentCreationForm
    template_name = "user/create_student.html"
    success_url = 'user:result'

    def get(self, request, *args, **kwargs):
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        temp = TempUtil(self.kwargs['pk'])
        temp_object = temp.get_object()

        # EdUer save
        eduser = temp.eduser_save()

        # Profile save
        profile = temp.profile_save()

        # Student save
        student = form.student_data(profile)
        student.gender = self.request.POST.get('gender')  # gender값은 StudentCreationForm에 없고, html에서 넘어옴 for radio btn
        student.save()

        # Temp delete
        temp_object.delete()

        return HttpResponseRedirect(reverse_lazy(self.get_success_url(), kwargs={'pk': eduser.id}))

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))


class SchoolAuthCreateView(FormView):
    form_class = SchoolAuthCreationForm
    template_name = "user/create_school_auth.html"
    success_url = 'user:result'

    def get(self, request, *args, **kwargs):
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        temp = TempUtil(self.kwargs['pk'])

        # EdUer save
        eduser = temp.eduser_save()

        # Profile save
        profile = temp.profile_save()

        # SchoolAuth save
        school = form.school_auth_data(profile)
        school.save()

        # Temp delete
        temp_object = temp.get_object()
        temp_object.delete()

        return HttpResponseRedirect(reverse_lazy(self.get_success_url(), kwargs={'pk': eduser.id}))


class TempUtil:
    def __init__(self, pk):
        self.temp = get_object_or_404(Temp, id=pk)
        self.choice = ['google', 'kakao', 'naver']

    def get_object(self):
        return self.temp

    def eduser_save(self):
        eduser_data = self.temp.eduser.split('| ')
        self.eduser = EdUser(email=eduser_data[0],
                             password=eduser_data[1],
                             nickname=eduser_data[2])

        if eduser_data[0].endswith(tuple(self.choice)):  # email의 끝글자가 self.choice 중 하나이면 True 반환
            self.eduser.set_password(None)
        self.eduser.save()
        return self.eduser

    def profile_save(self):
        profile_data = self.temp.profile.split('| ')
        profile = Profile(eduser=self.eduser,
                          group=profile_data[0],
                          phone=profile_data[1],
                          receive_email=profile_data[2])
        profile.save()
        return profile


class ResultCreateView(TemplateView):
    template_name = 'user/create_result.html'

    def get(self, request, *args, **kwargs):
        eduser = get_object_or_404(EdUser, id=kwargs['pk'])

        return render(request, self.template_name, {'eduser': eduser})


class TempDeleteView(RedirectView):
    def get(self, request, *args, **kwargs):
        temp = TempUtil(self.kwargs['pk'])
        temp_object = temp.get_object()
        temp_object.delete()
        return redirect('school:index')


# 여기서부터 마이페이지
class EdUserMypageView(TemplateView, LoginRequiredMixin):
    template_name = "user/mypage/index.html"

    def get(self, request, *args, **kwargs):
        email = self.request.user.get_username()
        eduser = EdUser.objects.get(email=email)
        pk = eduser.id
        kwargs.update({'pk': pk})
        return super().get(request, *args, **kwargs)


class PasswordChangeView(FormView, LoginRequiredMixin):
    form_class = PasswordChangeForm
    template_name = "user/mypage/change_password.html"
    success_url = reverse_lazy('user:login')

    def get_object(self):
        email = self.request.user.get_username()
        return get_object_or_404(EdUser, email=email)

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        eduser = self.get_object()
        form.user_update(eduser)
        return HttpResponseRedirect(self.get_success_url())


class ProfileUpdateView(UpdateView, LoginRequiredMixin):
    model = Profile
    context_object_name = 'profile'
    form_class = ProfileUpdateForm
    template_name = "user/mypage/update_profile.html"
    success_url = reverse_lazy('user:mypage')

    def get_initial(self):
        group = self.get_group()
        if group == "학생":
            student = self.get_student()
            self.initial = {
                'school': student.school,
                'grade': student.grade,
                'age': student.age,
                'address1': student.address1,
                'address2': student.address2,
            }
        return super().get_initial()

    def get_group(self):
        profile = self.get_object(queryset=None)
        return profile.group

    def get_student(self):
        pk = self.kwargs['pk']
        return get_object_or_404(Student, profile_id=pk)

    def form_valid(self, form):
        student = self.get_student()
        form.student_save(student)
        return super().form_valid(form)


# 여기서부터 소셜 로그인
class EduUserVerificationView(TemplateView):
    model = get_user_model()
    token_generator = default_token_generator

    def get(self, request, *args, **kwargs):
        if self.is_valid_token(**kwargs):
            messages.info(request, '인증이 완료되었습니다.')
        else:
            messages.info(request, '인증이 실패하였습니다.')

        return HttpResponseRedirect(reverse('user:login'))  # 인증 여부와 상관 없이 무조건 로그인 페이지로 이동

    def is_valid_token(self, **kwargs):
        pk = kwargs.get('pk')
        token = kwargs.get('token')
        user = self.model.objects.get(pk=pk)
        is_valid = self.token_generator.check_token(user, token)
        if is_valid:
            user.user_confirm = True
            user.save()
        return is_valid


class ResendVerificationEmailView(View, VerificationEmailMixin):
    model = get_user_model()

    def get(self, request):
        if request.user.is_authenticated and not request.user.user_confirm:
            try:
                user = self.model.objects.get(user_email=request.user.user_email)
            except self.model.DoesNotExist:
                messages.error(self.request, '알 수 없는 사용자 입니다.')
            else:
                self.send_verification_email(user)

        return HttpResponseRedirect(reverse('school:index'))


class SocialLoginCallbackView(NaverLoginMixin, View):

    success_url = reverse_lazy('school:index')
    failure_url = reverse_lazy('user:login')
    required_profiles = ['email', 'profile']
    model = get_user_model()
    oauth_user_id = None
    oauth_user_nickName = None
    is_success = False

    def get(self, request, **kwargs):
        provider = kwargs.get('provider')
        success_url = request.GET.get('next', self.success_url)

        if provider == 'naver':
            csrf_token = request.GET.get('state')
            code = request.GET.get('code')

            if not _compare_salted_tokens(csrf_token, request.COOKIES.get('csrftoken')):  # state(csrf_token)이 잘못된 경우
                messages.error(request, '잘못된 경로로 로그인하셨습니다.', extra_tags='danger')
                return HttpResponseRedirect(self.failure_url)
            is_success, error = self.login_or_create_with_naver(csrf_token, code)
            print('haohfoahsdofhoashdfoahdsohfohsdof')
            print(is_success)
            if not is_success:  # 로그인 or 생성 실패
                print('44444############################################################!$#@%$#$%#')
                messages.error(request, error, extra_tags='danger')
            return HttpResponseRedirect(success_url if is_success else self.failure_url)

        elif provider == 'google' or provider == 'kakao':
            self.work(provider)
        else:
            return HttpResponseRedirect(self.failure_url)

    def post(self, request, **kwargs):
        self.oauth_user_id = request.POST.get('id')
        self.oauth_user_nickName = request.POST.get('nickName')
        SocialLoginCallbackView.get(self, request, **kwargs)
        # is_success = request.user.is_authenticated
        return HttpResponseRedirect(self.success_url if self.is_success else self.failure_url)

    def work(self, provider):
        """
        기존 사용자는 login
        새로 가입하는 사용자는 Temp 테이블에 psv 형태로 저장 & user:profile url로 redirect
        """
        try:
            user = self.model.objects.get(email=self.oauth_user_id + '@social.' + provider)
            self.is_success = True
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        except ObjectDoesNotExist:  # EdUser 모델이 없을 경우
            if self.oauth_user_nickName == 'undefiend':
                self.oauth_user_nickName = self.oauth_user_id

            # Temp save
            data = self.oauth_user_id + '@social.' + provider + '| ' + \
                                                                'social_password' + '| ' + self.oauth_user_nickName
            temp = Temp(eduser=data)
            temp.create_date = timezone.now()
            temp.save()
            self.is_success = True
            self.success_url = reverse_lazy('user:profile', kwargs={'pk': temp.id})

    def set_session(self, **kwargs):
        for key, value in kwargs.items():
            self.request.session[key] = value


# self.send_verification_email(user)
#
#     response = super().form_valid(form)  # response == HttpResponseRedirect(self.get_success_url())
#     if form.instance:
#         self.send_verification_email(form.instance)
#     return response

