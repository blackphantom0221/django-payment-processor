# Generated by Django 3.0.5 on 2020-04-17 21:07

import django_fsm
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("getpaid", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="fraud_status",
            field=django_fsm.FSMField(
                choices=[
                    ("unknown", "unknown"),
                    ("accepted", "accepted"),
                    ("rejected", "rejected"),
                    ("check", "needs manual verification"),
                ],
                db_index=True,
                default="unknown",
                max_length=20,
                protected=True,
                verbose_name="fraud status",
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="status",
            field=django_fsm.FSMField(
                choices=[
                    ("new", "new"),
                    ("prepared", "in progress"),
                    ("pre-auth", "pre-authed"),
                    ("charge_started", "charge process started"),
                    ("partially_paid", "partially paid"),
                    ("paid", "paid"),
                    ("failed", "failed"),
                    ("refund_started", "refund started"),
                    ("refunded", "refunded"),
                ],
                db_index=True,
                default="new",
                max_length=50,
                protected=True,
                verbose_name="status",
            ),
        ),
    ]
