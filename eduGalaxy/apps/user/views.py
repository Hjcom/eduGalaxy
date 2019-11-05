from django.urls import reverse_lazy, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.edit import FormView, View, UpdateView, CreateView
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

from apps.user.forms import EdUserCreationForm, ProfileCreationForm, StudentCreationForm, SchoolAuthCreationForm, \
    ParentForm, ChildForm, EduLevelFormset, EduLevelForm
from apps.user.forms import ProfileUpdateForm, StudentUpdateForm, SchoolAuthUpdateForm, PasswordChangeForm
from apps.user.models import EdUser, Temp, Profile, Student, SchoolAuth, Parent, EduLevel, TempChild, Child

import os


# 회원가입
# 사용자 계정 뷰
class EdUserCreateView(FormView):
    form_class = EdUserCreationForm
    template_name = 'user/create_user.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        context = {'form': form}
        return render(request, self.template_name, context)

    def form_valid(self, form):
        temp = form.save(commit=False)
        temp.create_date = timezone.now()
        temp.save()
        eduser_id = temp.id
        return HttpResponseRedirect(reverse_lazy('user:profile', kwargs={'pk': eduser_id}))

    # validation error 시 필드값 초기화 및 에러 메시지 호출
    def form_invalid(self, form):
        # non_field_error() : error 메시지만 리턴
        error_data = form.non_field_errors()
        form = self.form_class(initial=self.initial)
        context = {
            'form': form,
            'error_msg': error_data
        }
        return render(self.request, self.template_name, context)


# 사용자 계정 세부내용
class ProfileCreateView(FormView):
    form_class = ProfileCreationForm
    template_name = 'user/create_profile.html'

    def get_object(self):
        pk = self.kwargs['pk']
        return get_object_or_404(Temp, id=pk)

    def get(self, request, *args, **kwargs):
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        print(request.POST)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        temp = self.get_object()
        data = form.profile_data()
        group = self.request.POST['group']
        pk = temp.id

        temp.profile = data
        temp.create_date = timezone.now()
        temp.save()

        if group == "학생":
            nexturl = 'user:student'
        elif group == "학교 관계자":
            nexturl = 'user:school_auth'
        elif group == "학부모":
            nexturl = 'user:parent'

        return HttpResponseRedirect(reverse_lazy(nexturl, kwargs={'pk': pk}))


# 사용자 - 학생 정보 입력
class StudentCreateView(FormView):
    form_class = StudentCreationForm
    template_name = "user/create_student.html"
    success_url = 'user:result'

    def get(self, request, *args, **kwargs):
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def form_valid(self, form):
        temp = TempUtil(self.kwargs['pk'])

        # EdUer save
        eduser = temp.eduser_save()

        # Profile save
        profile = temp.profile_save()

        # Student save
        student = form.student_data(profile)
        student.gender = self.request.POST.get('gender')  # gender값은 StudentCreationForm에 없고, html에서 넘어옴 for radio btn
        student.save()

        # EduLevel save
        edulevel = EduLevel(school=student.school,
                            status='재학중',
                            student_id=student.pk,
                            modified_cnt=0)
        edulevel.save()

        # 졸업한 학교가 있을 때
        graduated_school_list = self.request.POST.getlist('graduated_school')
        graduated_school_list = list(set(graduated_school_list))
        graduated_school_list.remove('')
        if student.school in graduated_school_list:
            graduated_school_list.remove(student.school)
        if graduated_school_list:
            for school in graduated_school_list:
                edulevel = EduLevel(school=school,
                                    status='졸업',
                                    student_id=student.pk,
                                    modified_cnt=0)
                edulevel.save()

        # Temp delete
        temp_object = temp.get_object()
        temp_object.delete()

        return HttpResponseRedirect(reverse_lazy(self.get_success_url(), kwargs={'pk': eduser.id}))


# 학부모 정보 입력
class ParentCreateView(CreateView):
    model = Parent
    form_class = ParentForm
    template_name = "user/create_parent.html"

    # 해당 자녀 데이터 필터(TempChild)
    def get_child(self):
        pk = self.kwargs['pk']
        temp = get_object_or_404(Temp, id=pk)
        return TempChild.objects.filter(temp=temp)

    def get(self, request, *args, **kwargs):
        self.object = None
        if self.get_child():
            kwargs.update({
               'children': self.get_child()
            })
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    # formset 정의
    def form_valid(self, form):

        temp = TempUtil(self.kwargs['pk'])

        # EdUer save
        eduser = temp.eduser_save()

        # Profile save
        profile = temp.profile_save()

        # 학부모 정보 저장
        parent = form.save(commit=False)
        parent.profile = profile
        parent.save()

        # tempchild 불러온 후 리스트형으로 변경
        child_query = self.get_child()
        children = list(child_query.values())

        # 자녀 정보 저장
        for child in children:
            child_data = Child(
                parent = parent,
                school = child['school'],
                grade = int(child['grade']),
                age = int(child['age']),
                gender = child['gender']
            )
            child_data.save()

            # 재학중인 학력 데이터 저장
            now_edulevel = EduLevel(
                school = child_data.school,
                status = "재학중",
                child = child_data
            )
            now_edulevel.save()

            # 졸업한 학력 데이터 저장
            child_edulevel = child['edulevel'].split('|')
            for edulevel in child_edulevel:
                finish_edulevel = EduLevel(
                    school = edulevel,
                    status = "졸업",
                    child = child_data
                )
                finish_edulevel.save()

        # Temp delete
        temp_object = temp.get_object()

        temp_children = self.get_child()
        for temp_child in temp_children:
            temp_child.delete()

        temp_object.delete()

        return HttpResponseRedirect(reverse_lazy('user:result', kwargs={'pk': eduser.id}))


# 자녀 정보 입력 뷰 - Tempchild
class TempChildCreateView(FormView):
    form_class = ChildForm
    template_name = "user/create_child.html"

    def get_object(self):
        pk = self.kwargs['pk']
        return get_object_or_404(Temp, id=pk)

    def get_formset(self):
        if self.request.method == 'POST':
            formset = EduLevelFormset(self.request.POST)
        else:
            formset = EduLevelFormset()
        return formset

    def get(self, request, *args, **kwargs):
        kwargs.update({'formsets': self.get_formset()})
        print(self.get_formset())
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        formsets = EduLevelFormset(self.request.POST)

        print(request.POST)
        print(form.is_valid())

        if form.is_valid():
            if formsets.is_valid():
                return self.formset_valid(form, formsets)
            else:
                return self.formset_invalid(form, formsets)
        else:
            return self.formset_invalid(form, formsets)

    def formset_valid(self, form, formsets):
        edulevel_list = []
        school = form.cleaned_data.get('school')

        # 졸업한 학교 리스트로 변경
        for formset in formsets:
            edulevel = formset.cleaned_data.get('edulevel')
            # 다니는 학교하고 다를 경우 리스트 값 추가
            if school != edulevel:
                edulevel_list.append(edulevel)

        # 리스트 중복 값 제거
        edulevel_list = list(set(edulevel_list))
        if None in edulevel_list:
            edulevel_list.remove(None)
        # 리스트에서 문자열로 변환 (|으로 조인)
        str_edulevel = '|'.join(edulevel_list)
        temp = self.get_object()

        # 자녀 데이터 모델에 저장
        temp_child = form.create_child()
        temp_child.edulevel = str_edulevel
        temp_child.temp = temp
        temp_child.save()

        return HttpResponseRedirect(reverse_lazy('user:parent', kwargs={'pk': temp.id}))

    def formset_invalid(self, form, formsets):
        context = {
            'form': form,
            'formsets': formsets
        }
        return self.render_to_response(context)

# 자녀 정보 삭제 뷰
class TempChildDeleteView(RedirectView):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        tempchild = get_object_or_404(TempChild, id=pk)
        temp = tempchild.temp

        tempchild.delete()
        return HttpResponseRedirect(reverse_lazy('user:parent', kwargs={'pk': temp.id}))


# 사용자 - 학교 관계자 정보
class SchoolAuthCreateView(FormView):
    form_class = SchoolAuthCreationForm
    template_name = "user/create_school_auth.html"
    success_url = 'user:result'

    def get(self, request, *args, **kwargs):
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def form_valid(self, form):
        temp = TempUtil(self.kwargs['pk'])

        # EdUer save
        eduser = temp.eduser_save()

        # Profile save
        profile = temp.profile_save()

        # SchoolAuth save
        school_auth = form.school_auth_data(profile)
        school_auth.save()

        # Temp delete
        temp_object = temp.get_object()
        temp_object.delete()

        return HttpResponseRedirect(reverse_lazy(self.get_success_url(), kwargs={'pk': eduser.id}))


# temp 데이터 관련 class
class TempUtil:
    def __init__(self, pk):
        self.temp = get_object_or_404(Temp, id=pk)
        self.provider = None

    def get_object(self):
        return self.temp

    def eduser_save(self):
        eduser_data = self.temp.eduser.split('| ')
        self.eduser = EdUser(email=eduser_data[0])
        self.eduser.set_password(eduser_data[1])

        if len(eduser_data) > 2:
            self.eduser.set_password(None)
            self.provider = eduser_data[-1]

        self.eduser.save()
        return self.eduser

    def profile_save(self):
        profile_data = self.temp.profile.split('| ')
        profile = Profile(eduser=self.eduser,
                          group=profile_data[0],
                          phone=profile_data[1],
                          receive_email=profile_data[2])

        # self.provider에 따른 컬럼값(default == False) 수정
        if self.provider is not None:
            profile.confirm = True
            if self.provider == 'naver':
                profile.is_naver = True
            elif self.provider == 'google':
                profile.is_google = True
        profile.save()
        return profile


class ResultCreateView(TemplateView, VerificationEmailMixin):
    template_name = 'user/create_result.html'

    def get(self, request, *args, **kwargs):
        eduser = get_object_or_404(EdUser, id=kwargs['pk'])

        if eduser.profile.confirm is False:  # 소셜 회원가입이 아니면 이메일 발송
            self.send_verification_email(eduser)

        return render(request, self.template_name, {'eduser': eduser})


class TempDeleteView(RedirectView):
    def get(self, request, *args, **kwargs):
        temp = TempUtil(self.kwargs['pk'])
        temp_object = temp.get_object()

        tempchild = TempChild.objects.filter(temp=temp_object)
        if tempchild.exists():
            tempchild.delete()

        temp_object.delete()
        return redirect('school:index')


# 여기서부터 마이페이지
class EdUserMypageView(TemplateView, LoginRequiredMixin):
    template_name = "user/mypage/index.html"

    def get(self, request, *args, **kwargs):
        email = self.request.user.get_username()
        eduser = EdUser.objects.get(email=email)
        kwargs.update({'pk': eduser.id})
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
        old_pwd = request.POST.get('old_pwd')
        if not request.user.check_password(old_pwd):
            form.add_error(None, "기존 비밀번호를 잘못 입력하셨습니다.")

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        user = self.get_object()
        form.user_update(user)
        return HttpResponseRedirect(self.get_success_url())


# 프로필 수정
class ProfileUpdateView(UpdateView, LoginRequiredMixin):
    model = Profile
    form_class = ProfileUpdateForm
    context_object_name = 'profile'
    template_name = 'user/mypage/update_profile.html'
    success_url = reverse_lazy('user:mypage')

    def get_object(self):
        profile = get_object_or_404(Profile, pk=self.request.user.pk)
        print(profile)

        return profile


class StudentUpdateView(UpdateView, LoginRequiredMixin):
    model = Student
    form_class = StudentUpdateForm
    context_object_name = 'student'
    template_name = 'user/mypage/update_student.html'
    success_message = '수정이 완료 되었습니다.'
    success_url = reverse_lazy('user:update_student')

    def get_object(self):
        student = get_object_or_404(Student, pk=self.request.user.pk)

        return student

    def form_valid(self, form):
        messages.add_message(self.request, messages.SUCCESS, self.success_message)

        return super().form_valid(form)


class SchoolAuthUpdateView(UpdateView, LoginRequiredMixin):
    model = SchoolAuth
    form_class = SchoolAuthUpdateForm
    context_object_name = 'school_auth'
    template_name = 'user/mypage/update_school_auth.html'
    success_message = '수정이 완료 되었습니다.'
    success_url = reverse_lazy('user:update_school_auth')

    def get_object(self):
        school_auth = get_object_or_404(SchoolAuth, pk=self.request.user.pk)

        return school_auth

    def get_file(self):
        file = SchoolAuth.objects.values_list('auth_doc', flat=True).get(profile_id=self.request.user.pk)

        return file

    def form_valid(self, form):
        file = self.get_file()
        file_path = "media/" + file

        if os.path.isfile(file_path):
            os.remove(file_path)

        messages.add_message(self.request, messages.SUCCESS, self.success_message)

        return super().form_valid(form)


class ParentUpdateView(UpdateView, LoginRequiredMixin):
    model = Parent
    form_class = ParentForm
    context_object_name = 'parent'
    template_name = 'user/mypage/update_parent.html'
    success_url = reverse_lazy('user:update_profile')

    def get_child(self):
        self.kwargs.update({'pk': self.request.user.pk})
        parent = self.get_object()
        child = Child.objects.filter(parent_id=parent.pk)

        return child

    def get(self, request, *args, **kwargs):
        kwargs.update({'children': self.get_child(),
                       'parent': self.get_object()})
        self.object = self.get_object()
        return render(self.request, self.template_name, self.get_context_data(**kwargs))


class ChildAddView(CreateView, LoginRequiredMixin):
    model = Child
    form_class = ChildForm
    template_name = "user/mypage/add_child.html"

    def get_parent(self):
        return get_object_or_404(Parent, pk=self.request.user.pk)

    def get_formset(self):
        if self.request.method == 'POST':
            formset = EduLevelFormset(self.request.POST)
        else:
            formset = EduLevelFormset()
        return formset

    def get(self, request, *args, **kwargs):
        self.object = None
        kwargs.update({'formsets': self.get_formset(),
                       'parent': self.get_parent()})
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formsets = self.get_formset()

        if form.is_valid():
            if formsets.is_valid():
                return self.formset_valid(form, formsets)
            else:
                return self.formset_invalid(form, formsets)
        else:
            return self.formset_invalid(form, formsets)

    def formset_valid(self, form, formsets):
        edulevel_list = []
        school = form.cleaned_data.get('school')

        # 졸업한 학교 리스트로 변경
        for formset in formsets:
            edulevel = formset.cleaned_data.get('edulevel')
            # 다니는 학교하고 다를 경우 리스트 값 추가
            if school != edulevel:
                edulevel_list.append(edulevel)

        # 리스트 중복 값 제거
        edulevel_list = list(set(edulevel_list))
        if None in edulevel_list:
            edulevel_list.remove(None)

        # 자녀 데이터 모델에 저장
        child = form.save(commit=False)
        child.parent = self.get_parent()
        child.save()

        # 재학중인 학력 데이터 저장
        now_edulevel = EduLevel(
            school=child.school,
            status="재학중",
            child=child
        )
        now_edulevel.save()

        # 졸업한 학력 데이터 저장
        for edulevel in edulevel_list:
            finish_edulevel = EduLevel(
                school=edulevel,
                status="졸업",
                child=child
            )
            finish_edulevel.save()

        return redirect('user:update_parent')

    def formset_invalid(self, form, formsets):
        context = {
            'form': form,
            'formsets': formsets,
            'parents': self.get_parent()
        }
        return self.render_to_response(context)


class ChildUpdateView(UpdateView, LoginRequiredMixin):
    model = Child
    form_class = ChildForm
    context_object_name = 'child'
    template_name = "user/mypage/update_child.html"
    success_url = reverse_lazy('user:update_parent')

    def get_parent(self):
        return get_object_or_404(Parent, pk=self.request.user.pk)

    def get_edu_level(self):
        child = self.get_object()
        edu_level = EduLevel.objects.filter(child_id=child.pk) \
            .exclude(status='재학중')

        return edu_level


    def get(self, request, *args, **kwargs):
        self.object = self.get_object()

        kwargs.update({
            'parent': self.get_parent(),
            'edu_levels': self.get_edu_level()
        })
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

class ChildDeleteView(RedirectView):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        child = get_object_or_404(Child, id=pk)

        child.delete()
        return HttpResponseRedirect(reverse_lazy('user:update_parent'))


class ChildEduLevelCreateView(FormView, LoginRequiredMixin):
    form_class = EduLevelForm
    template_name = "user/mypage/create_child_edulevel.html"
    success_url = 'user:update_child'

    def get_child(self):
        pk = self.kwargs['pk']
        return get_object_or_404(Child, pk=pk)

    def get_parent(self):
        return get_object_or_404(Parent, pk=self.request.user.pk)

    def get(self, requset, *args, **kwargs):
        kwargs.update({'parent': self.get_parent()})
        return render(self.request, self.template_name, self.get_context_data(**kwargs))


    def form_valid(self, form):
        child = self.get_child()
        edulevel = form.create_edulevel()
        edulevel.child = child
        edulevel.save()

        return HttpResponseRedirect(reverse_lazy(self.success_url, kwargs={'pk': child.pk}))


class ChildEduLevelUpdateView(FormView, LoginRequiredMixin):
    form_class = EduLevelForm
    template_name = "user/mypage/update_child_edulevel.html"
    success_url = 'user:update_child'

    def get_initial(self):
        edu_level = self.get_edu_level()

        self.initial = {
            'edulevel': edu_level.school
        }
        return super().get_initial()

    def get_edu_level(self):
        pk = self.kwargs['pk']
        return get_object_or_404(EduLevel, pk=pk)

    def get_parent(self):
        return get_object_or_404(Parent, pk=self.request.user.pk)

    def get(self, requset, *args, **kwargs):
        kwargs.update({'parent': self.get_parent()})
        return render(self.request, self.template_name, self.get_context_data(**kwargs))

    def form_valid(self, form):
        edu_level = self.get_edu_level()
        edu_level.school = form.cleaned_data.get('edulevel')
        child = edu_level.child
        edu_level.save()

        return HttpResponseRedirect(reverse_lazy(self.success_url, kwargs={'pk': child.pk}))


class ChildEdulevelDeleteView(RedirectView):
    def get(self, request, *args, **kwargs):
        pk = self.kwargs['pk']
        edu_level = get_object_or_404(EduLevel, pk=pk)
        child = edu_level.child
        edu_level.delete()
        return HttpResponseRedirect(reverse_lazy('user:update_child', kwargs={'pk': child.pk}))

# 학생 학력 수정 뷰
class EduLevelUpdateView(View, LoginRequiredMixin):
    template_name = 'user/mypage/update_edulevel.html'
    redirect_url = 'user:mypage'

    def get(self, request, *args, **kwargs):
        graduated_school = EduLevel.objects.filter(student_id=kwargs.get('pk'))\
                                           .exclude(status='재학중')
        student = Student.objects.get(pk=kwargs.get('pk'))
        return render(request, self.template_name, {'student': student, 'graduated_school': graduated_school})

    def post(self, request, **kwargs):
        # 입력받은 졸업학교 리스트를 전처리
        graduated_school_list = self.request.POST.getlist('graduated_school')
        graduated_school_list = list(set(graduated_school_list))
        graduated_school_list.remove('')

        # GET EduLevel multiple objects
        edulevel = EduLevel.objects.filter(student_id=request.user.pk)

        # 재학중인 학교가 입력받은 학교에 있을 때
        if edulevel.get(status='재학중').school in graduated_school_list:
            graduated_school_list.remove(edulevel.get(status='재학중').school)

        try:
            # 졸업한 학교들을 리스트로 저장
            edulevel_graduated_school_list = []
            for i in edulevel.filter(status='졸업'):
                edulevel_graduated_school_list.append(i.school)

            # 입력받은 졸업학교 리스트와 저장돼 있는 학교들을 비교 & graduated_school_list 수정
            graduated_school_list = [x for x in graduated_school_list if x not in edulevel_graduated_school_list]
        except:
            # messages.error()
            pass
        finally:
            if graduated_school_list:
                for school in graduated_school_list:
                    edulevel = EduLevel(school=school,
                                        status='졸업',
                                        student_id=request.user.pk,
                                        modified_cnt=1)
                    edulevel.save()

        return redirect(self.redirect_url)


# 회원 탈퇴 뷰
class EdUserDeleteView(RedirectView, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        eduser = get_object_or_404(EdUser, id=kwargs['pk'])
        eduser.delete()
        return redirect('school:index')


# 이메일 전송 뷰
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
        profile = Profile.objects.get(eduser_id=pk)
        is_valid = self.token_generator.check_token(user, token)
        if is_valid:
            profile.confirm = True
            profile.save()
        return is_valid


# 여기서부터 소셜 로그인
class ResendVerificationEmailView(View, VerificationEmailMixin):
    model = get_user_model()

    def get(self, request):
        if request.user.is_authenticated and not request.user.confirm:
            try:
                user = self.model.objects.get(email=request.user.email)
            except self.model.DoesNotExist:
                messages.error(self.request, '알 수 없는 사용자 입니다.')
                # messages.add_message(self.request, messages.error, '같은 이메일로 가입된 정보가 있습니다. '
                #                        '본인 확인용 메일을 보내드렸습니다. 인증 후 연동 가능합니다.')
            else:
                self.send_verification_email(user)

        return HttpResponseRedirect(reverse('school:index'))


class SocialLoginCallbackView(NaverLoginMixin, View, VerificationEmailMixin):

    failure_url = reverse_lazy('user:login')
    required_profiles = ['email']
    model = get_user_model()
    is_success = False

    def get(self, request, **kwargs):
        provider = kwargs.get('provider')

        if provider == 'naver':
            csrf_token = request.GET.get('state')
            code = request.GET.get('code')

            if not _compare_salted_tokens(csrf_token, request.COOKIES.get('csrftoken')):  # state(csrf_token)이 잘못된 경우
                messages.error(request, '잘못된 경로로 로그인하셨습니다.', extra_tags='danger')
                # messages.add_message(self.request, messages.error, '같은 이메일로 가입된 정보가 있습니다. '
                #                        '본인 확인용 메일을 보내드렸습니다. 인증 후 연동 가능합니다.')
                return HttpResponseRedirect(self.failure_url)
            is_success, data = self.login_or_create_with_naver(csrf_token, code)
            if not is_success:  # 로그인 or 생성 실패
                if type(data) is list:  # profile.confirm 이 False 일때는 data가 리스트형태로 리턴
                    user = data[2]
                    self.send_verification_email(user)
                    messages.error(request, data[0], extra_tags='danger')
                    # messages.add_message(self.request, messages.error, '같은 이메일로 가입된 정보가 있습니다. '
                    #                        '본인 확인용 메일을 보내드렸습니다. 인증 후 연동 가능합니다.')
                    return HttpResponseRedirect(data[1])
                else:
                    messages.error(request, data, extra_tags='danger')
                    # messages.add_message(self.request, messages.error, '같은 이메일로 가입된 정보가 있습니다. '
                    #                        '본인 확인용 메일을 보내드렸습니다. 인증 후 연동 가능합니다.')
            return HttpResponseRedirect(data if is_success else self.failure_url)
        else:
            return HttpResponseRedirect(self.failure_url)

    def post(self, request, **kwargs):
        provider = kwargs.get('provider')
        self.oauth_user_email = request.POST.get('email')
        if provider == 'google':
            data = self.work(request)
            return HttpResponseRedirect(data)
        else:
            return HttpResponseRedirect(self.failure_url)

    def work(self, request):
        """
        기존 사용자는 login
        새로 가입하는 사용자는 Temp 테이블에 psv 형태로 저장 & user:profile url로 redirect
        """
        # 사용자 로그인 or 생성
        try:
            # 유저 검색
            user = self.model.objects.get(email=self.oauth_user_email)
            profile = Profile.objects.get(eduser_id=user.id)
            if not profile.is_google:  # 기존 유저는 있지만 소셜 연동(google)을 하지 않았을 때
                if profile.confirm:
                    profile.is_google = True
                    profile.save()
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                else:
                    # messages.error(request, '같은 이메일로 가입된 정보가 있습니다. '
                    #                        '본인 확인용 메일을 보내드렸습니다. 인증 후 연동 가능합니다.')
                    messages.add_message(self.request, messages.error, '같은 이메일로 가입된 정보가 있습니다. '
                                                                       '본인 확인용 메일을 보내드렸습니다. '
                                                                       '인증 후 연동 가능합니다.')
                    self.send_verification_email(user)  # email resend
            else:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        except ObjectDoesNotExist:  # EdUser 모델이 없을 경우
            # Temp save
            data = self.oauth_user_email + '| ' + 'social_password' + '| ' + 'google'

            temp = Temp(eduser=data)
            temp.create_date = timezone.now()
            temp.save()

            return reverse_lazy('user:profile', kwargs={'pk': temp.id})

        return reverse_lazy('school:index')

    def set_session(self, **kwargs):
        for key, value in kwargs.items():
            self.request.session[key] = value

