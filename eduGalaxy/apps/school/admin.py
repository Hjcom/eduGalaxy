from apps.school.models import Info, CsvFile, Post, Review
from apps.school.forms import SaveCSVForm, UploadFileForm
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages

import csv
import os


class SchoolCsvFileAdmin(admin.ModelAdmin):
    change_list_template = 'admin/CSVFile_change_list.html'

    list_display = (
        'id',
        'file_name',
        'file_use',
    )
    list_display_links = ['id', 'file_name']

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("import-csv/", self.import_csv),
            path("manage-csv/", self.manage_csv),
        ]
        return my_urls + urls

    def import_csv(self, request):
        if request.method == "POST":
            form = UploadFileForm(request.POST, request.FILES)
            upload_file = request.FILES['file']
            if form.is_valid():
                csv_file = form.save(commit=False)
                csv_file.file_name = upload_file.name
                csv_file.save()
                self.message_user(request, "csv 저장 완료")

                return redirect("..")
        else:
            form = UploadFileForm()
        return render(request, "admin/csv_import.html", {'form': form})

    def manage_csv(self, request):
        if request.method == "POST":
            form = SaveCSVForm(request.POST)
            file = 'media/'

            if form.is_valid():
                file_id = form.cleaned_data['csv_select']

                if file_id == '0':
                    messages.error(request, "파일을 선택하세요")
                    form = SaveCSVForm()
                    return render(request, "admin/csv_list.html", {'form': form})
                file_name = CsvFile.objects.filter(pk=file_id).values_list('file', flat=True)
                file = file + file_name[0]

                if 'save' in request.POST:
                    with open(file, encoding='euc-kr') as f:
                        reader = csv.reader(f, delimiter=',')
                        con = 0
                        for row in reader:
                            if con > 0:
                                school = form.save(row, commit=False)
                                school.published_date = timezone.now()
                                school.save()
                            con += 1
                    self.message_user(request, "school DB 저장완료")
                    return redirect("..")
                elif 'delete' in request.POST:
                    if file_id == 0:
                        messages.error(request, "파일을 선택하세요")
                        form = SaveCSVForm()
                        return render(request, "admin/csv_list.html", {'form': form})
                    csv_file = CsvFile(pk=file_id)
                    csv_file.delete()
                    if os.path.isfile(file):
                        os.remove(file)
                    self.message_user(request, "해당 파일 삭제")
                return redirect("..")
        else:
            form = SaveCSVForm()
        return render(request, "admin/csv_list.html", {'form': form})


admin.site.register(CsvFile, SchoolCsvFileAdmin)
admin.site.register(Info)
admin.site.register(Post)
admin.site.register(Review)
