from django import forms
from django.forms import formset_factory

from django.utils.translation import ugettext as _

from apps.user.models import EdUser, Temp, TempChild, Log, Profile
from apps.user.models import SchoolAuth, Student, Parent, Child, EduLevel

EMAIL_LIST = (
    ("select", "선택하세요"),
    ("naver.com", "naver.com"),
    ("gmail.com", "gmail.com"),
    ("hanmail.net", "hanmail.net"),
    ("nate.com", "nate.com"),
    ("daum.net", "daum.net"),
    ("hotmail.com", "hotmail.com"),
    ("direct", "직접 입력")
)

GROUP_LIST = (
    ("select", "선택하세요"),
    ("학생", "학생"),
    ("학부모", "학부모"),
    ("학교 관계자", "학교 관계자")
)

GENDER_LIST = (
    ("남", "남"),
    ("여", "여")
)


# user 계정 폼
class EdUserCreationForm(forms.Form):
    email1 = forms.CharField(widget=forms.TextInput(
            attrs={
                'autofocus': 'autofocus',
                'required': 'required',
            }),
        label='이메일'
    )

    email2 = forms.CharField(widget=forms.TextInput(
            attrs={
                'id': 'user_email2',
                'disabled': 'disabled',
            })
    )

    # 이메일 선택 리스트 선택시 Change_Email() 함수 호출
    select_email = forms.CharField(widget=forms.Select(
        choices=EMAIL_LIST,
        attrs={
                'id': 'select',
                'onchange': 'Change_Email();'}
        )
    )

    password1 = forms.CharField(
        label=_("비밀번호"),
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label=_("비밀번호 확인"),
        strip=False,
        widget=forms.PasswordInput
    )

    # 폼 유효성 검사
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')

        email = cleaned_data['email1'] + "@" + cleaned_data['email2']

        check_email = EdUser.objects.filter(email=email)

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("비밀번호 오류입니다. 다시 입력해주세요")
        if check_email.exists():
            raise forms.ValidationError("해당 이메일은 이미 가입하셨습니다.")

        return super().clean()

    # cleaned_data temp에 저장
    def save(self, commit=True):
        email1 = self.cleaned_data.get('email1')
        email2 = self.cleaned_data.get('email2')
        password = self.cleaned_data.get("password1")

        email = email1 + "@" + email2

        eduser = email + "| " + password
        temp = Temp(eduser=eduser)

        if commit:
            temp.save()

        return temp


# user 세부 정보 폼
class ProfileCreationForm(forms.Form):
    group = forms.CharField(widget=forms.Select(
            choices=GROUP_LIST,
            attrs={'id': 'group'}
        ),
        label="직업"
    )
    phone = forms.CharField(label='핸드폰 번호', widget=forms.TextInput, required=False)
    receive_email = forms.BooleanField(
        label='이메일 수신 동의',
        required=False,
    )

    # 본인인증 여부는 추후 구현 예정(핸드폰 인증/이메일 인증)
    # phone 필드는 수정이 필요한 부분
    def profile_data(self):
        group = self.cleaned_data.get('group')
        phone = self.cleaned_data.get('phone')
        receive_email = self.cleaned_data.get('receive_email')

        if receive_email:
            data = group + "| " + phone + "| " + "True"
        else:
            data = group + "| " + phone + "| " + "False"
        return data


class StudentCreationForm(forms.Form):
    school = forms.CharField(label='다니는 학교', widget=forms.TextInput)
    grade_list = range(0, 7)
    GRADE = []
    for grade in grade_list:
        if grade == 0:
            GRADE.append([grade, " "])
        else:
            GRADE.append([grade, str(grade)])

    grade = forms.CharField(widget=forms.Select(
        choices=tuple(GRADE),
        attrs={'name': 'grade'},
    ),
        label='학년'
    )

    # 나이 select 위젯 선언
    age_list = range(0, 101)
    AGE_CONTROL = []
    for age in age_list:
        if age == 0:
            AGE_CONTROL.append([age, " "])
        else:
            AGE_CONTROL.append([age, str(age)])

    age = forms.CharField(widget=forms.Select(
            choices=tuple(AGE_CONTROL),
            attrs={'name': 'age'},
        ),
        label='나이'
    )
    address1 = forms.CharField(
        label='주소',
        widget=forms.TextInput(
            attrs={'id': 'address1'}
        )
    )
    address2 = forms.CharField(
        label='상세 주소',
        widget=forms.TextInput(
            attrs={'id': 'address2'}
        )
    )

    # 학력 추가 필요
    def student_data(self, profile):
        school = self.cleaned_data.get('school')
        grade = self.cleaned_data.get('grade')
        age = self.cleaned_data.get('age')
        address1 = self.cleaned_data.get('address1')
        address2 = self.cleaned_data.get('address2')

        student = Student(profile=profile,
                          school=school,
                          grade=grade,
                          age=age,
                          address1=address1,
                          address2=address2)
        return student


class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = ('address1', 'address2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['address1'].widget.attrs = {'id': 'address1'}
        self.fields['address2'].widget.attrs = {'id': 'address2'}


class ChildForm(forms.ModelForm):
    class Meta:
        # grade choice list 정의
        grade_list = range(0, 7)
        GRADE = []
        for grade in grade_list:
            if grade == 0:
                GRADE.append([grade, " "])
            else:
                GRADE.append([grade, str(grade)])

        # age choice list 정의
        age_list = range(0, 101)
        AGE_CONTROL = []
        for age in age_list:
            if age == 0:
                AGE_CONTROL.append([age, " "])
            else:
                AGE_CONTROL.append([age, str(age)])

        model = Child
        fields = ('school', 'grade', 'age', 'gender')
        labels = {
            'school': '다니는 학교',
            'grade' : '학년',
            'age'   : '나이',
            'gender': '성별'
        }
        widgets = {
            'grade': forms.Select(choices=tuple(GRADE), attrs={'name': 'grade'}),
            'age': forms.Select(choices=tuple(AGE_CONTROL), attrs={'name': 'age'}),
            'gender': forms.RadioSelect(choices=GENDER_LIST, attrs={'style': 'display: inline-block', 'id': 'gender'})
        }

    # 자녀 정보 추가
    def create_child(self):
        child = TempChild(
            school=self.cleaned_data.get('school'),
            grade=self.cleaned_data.get('grade'),
            age=self.cleaned_data.get('age'),
            gender=self.cleaned_data.get('gender')
        )
        return child


# Temp 학력 폼
class EduLevelForm(forms.Form):
    edulevel = forms.CharField(
        label='졸업한 학교',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control'
            }
        )
    )

    def create_edulevel(self):
        edulevel = EduLevel(
            school=self.cleaned_data.get('edulevel'),
            status="졸업"
        )
        return edulevel



EduLevelFormset = formset_factory(EduLevelForm, extra=1)


class SchoolAuthCreationForm(forms.ModelForm):
    class Meta:
        model = SchoolAuth
        fields = ('school', 'auth_doc', 'tel')

    def __init__(self, *args, **kwargs):
        super(SchoolAuthCreationForm, self).__init__(*args, **kwargs)
        self.fields['auth_doc'].required = False
        self.fields['tel'].required = False

    def school_auth_data(self, profile):
        school = self.cleaned_data.get('school')
        tel = self.cleaned_data.get('tel')
        auth_doc = self.cleaned_data.get('auth_doc')

        school_auth = SchoolAuth(profile=profile,
                                 school=school,
                                 tel=tel,
                                 auth_doc=auth_doc)
        return school_auth


class PasswordChangeForm(forms.Form):
    old_pwd = forms.CharField(
        label=_("기존 비밀번호"),
        strip=False,
        widget=forms.PasswordInput,
    )
    new_pwd1 = forms.CharField(
        label=_("새로운 비밀번호"),
        strip=False,
        widget=forms.PasswordInput,
    )
    new_pwd2 = forms.CharField(
        label=_("비밀번호 확인"),
        strip=False,
        widget=forms.PasswordInput,
    )

    def clean(self):
        cleaned_data = super().clean()

        old_pwd = cleaned_data.get('old_pwd')
        new_pwd1 = cleaned_data.get('new_pwd1')
        new_pwd2 = cleaned_data.get('new_pwd2')

        if new_pwd2 == old_pwd:
            raise forms.ValidationError("기존 비밀번호와 새로운 비밀번호랑 달라야합니다.")
        if new_pwd1 != new_pwd2:
            raise forms.ValidationError("비밀번호가 서로 다릅니다!")

    def user_update(self, user):
        password = self.cleaned_data.get('new_pwd2')
        user.password = password

        user.set_password(password)
        user.save()


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('phone', 'receive_email')


class StudentUpdateForm(forms.ModelForm):
    class Meta:
        grade_list = range(0, 7)
        GRADE = []
        for grade in grade_list:
            if grade == 0:
                GRADE.append([grade, " "])
            else:
                GRADE.append([grade, str(grade)])

        age_list = range(0, 101)
        AGE_CONTROL = []
        for age in age_list:
            if age == 0:
                AGE_CONTROL.append([age, " "])
            else:
                AGE_CONTROL.append([age, str(age)])

        model = Student
        exclude = ('profile',)
        widgets = {
            'grade': forms.Select(choices=tuple(GRADE), attrs={'name': 'grade'}),
            'age': forms.Select(choices=tuple(AGE_CONTROL), attrs={'name': 'age'}),
            'gender': forms.RadioSelect(choices=GENDER_LIST, attrs={'style': 'display: inline-block', 'id': 'gender'})
        }


class SchoolAuthUpdateForm(forms.ModelForm):
    # school = forms.CharField(label='학교', widget=forms.TextInput)
    # auth_doc = forms.FileField(label='인증서류')
    # tel = forms.CharField(label='사무실 연락처', max_length=15)

    class Meta:
        model = SchoolAuth
        exclude = ('profile',)

