# Generated by Django 2.1.4 on 2019-03-04 10:11

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0009_alter_user_last_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='EduGalaxyUser',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('user_email', models.EmailField(max_length=50, unique=True, verbose_name='아이디')),
                ('user_nickname', models.CharField(max_length=15, verbose_name='닉네임')),
                ('user_age', models.IntegerField(default=28, verbose_name='나이')),
                ('user_job', models.CharField(max_length=30, verbose_name='직업')),
                ('user_sex', models.BooleanField(default=False, verbose_name='성별')),
                ('user_address1', models.CharField(max_length=100)),
                ('user_address2', models.CharField(max_length=100)),
                ('user_phone', models.CharField(max_length=15, verbose_name='핸드폰 번호')),
                ('user_receive_email', models.BooleanField(default=False, verbose_name='알림 동의 여부')),
                ('user_confirm', models.BooleanField(default=False, verbose_name='본인인증 여부')),
                ('user_signup_ip', models.CharField(max_length=20, verbose_name='가입 ip')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date joined')),
                ('is_active', models.BooleanField(default=True, verbose_name='활성화 여부')),
                ('is_superuser', models.BooleanField(default=False, verbose_name='관리자 여부')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'edugalaxyuser',
                'verbose_name': '유저',
                'ordering': ('-date_joined',),
                'verbose_name_plural': '유저들',
            },
        ),
    ]
