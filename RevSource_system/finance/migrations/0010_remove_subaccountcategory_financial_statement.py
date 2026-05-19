from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0009_subaccountcategory_account_subcategory'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subaccountcategory',
            name='financial_statement',
        ),
    ]
