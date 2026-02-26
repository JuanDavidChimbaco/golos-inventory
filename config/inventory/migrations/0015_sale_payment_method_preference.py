from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventory", "0014_sale_shipping_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="payment_method_preference",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]

