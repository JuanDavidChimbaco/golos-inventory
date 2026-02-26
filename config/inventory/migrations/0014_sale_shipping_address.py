from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0013_shipment_shipmentevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="shipping_address",
            field=models.JSONField(blank=True, null=True),
        ),
    ]

