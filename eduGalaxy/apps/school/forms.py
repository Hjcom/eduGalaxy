from django import forms

from apps.school.models import CsvFile, Info


class SaveCSVForm(forms.Form):
    csv_dint = CsvFile.objects.filter().values('id', 'file').order_by('file')

    select_file = [
        [0, "파일 선택"]
    ]

    for csv_list in csv_dint:
        csv_file = csv_list['file']
        select_file.append([csv_list['id'], csv_file[16:]])

    csv_select = forms.CharField(
        widget=forms.Select(
            choices=tuple(select_file),
            attrs={'id': 'csv_select'}
        ),
        label="CSV 파일 리스트"
    )

    def save(self, row, commit=True):
        school = Info()

        school.ooe = row[0]
        school.lea = row[1]
        school.location = row[2]

        school.code = row[3]
        school.name = row[4]
        school.grade_code = int(row[5])

        school.estab_div = row[6]
        school.char = row[7]

        if row[8] == 'Y':
            school.has_branches = True
        else:
            school.has_branches = False

        school.estab_type = row[9]
        school.day_n_night = row[10]
        school.anniversary = row[11]
        school.estab_date = row[12]

        school.dong_code = row[13]
        school.address1 = row[14]
        school.address2 = row[15]
        school.zip_code = row[16]
        school.zip_code_st = row[17]
        school.address1_st = row[18]
        school.address2_st = row[19]

        school.lat = float(row[20])
        school.lng = float(row[21])

        school.phone = row[22]
        school.fax = row[23]
        school.homepage = row[24]

        school.gender_div = row[25]
        school.num_student = row[26]
        school.num_teacher = row[27]

        if commit:
            school.save()
        return school


class UploadFileForm(forms.ModelForm):
    class Meta:
        model = CsvFile
        fields = ('file', 'file_use')

    def __init__(self, *args, **kwargs):
        super(UploadFileForm, self).__init__(*args, **kwargs)
        self.fields['file'].required = True


# class PostForm(forms.ModelForm):
#
#     class Meta:
#         model = AdminPost
#         fields = ()
