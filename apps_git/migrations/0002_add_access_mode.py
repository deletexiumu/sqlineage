# Generated manually for adding access_mode field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apps_git', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gitrepo',
            name='access_mode',
            field=models.CharField(
                choices=[('clone', '本地克隆'), ('api', 'API访问')],
                default='clone',
                help_text='访问模式：本地克隆或API访问',
                max_length=10
            ),
        ),
    ]