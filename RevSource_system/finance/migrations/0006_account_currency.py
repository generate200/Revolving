# Generated migration for adding currency field to Account model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finance', '0005_journalentry_entry_type_alter_account_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='currency',
            field=models.ForeignKey(
                blank=True,
                help_text="Currency in which this account's balance is stored. NULL means base currency.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='finance.currency',
            ),
        ),
    ]
