from django.db import models

# Create your models here.

class Product(models.Model): 
    name = models.CharField(max_length=100) 
    brand = models.CharField(max_length=50) 
    description = models.TextField(blank=True, null=True) 
    active = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.CharField(max_length=50) # mientras se usa user
    updated_by = models.CharField(max_length=50) # mientras se usa user
    
    def __str__(self): return self.name
     
class ProductImage(models.Model): 
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='images') 
    image = models.ImageField(upload_to='products/') 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.CharField(max_length=50) # mientras se usa user
    updated_by = models.CharField(max_length=50) # mientras se usa user
    
    def __str__(self): return f"Image for {self.product.name}" 
    
class ProductVariant(models.Model): 
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='variants') 
    gender = models.CharField(max_length=10 , choices=[('male', 'Male'), ('female', 'Female'), ('unisex', 'Unisex')]) 
    color = models.CharField(max_length=50) size = models.CharField(max_length=10) 
    price = models.DecimalField(max_digits=10, decimal_places=2) 
    cost = models.DecimalField(max_digits=10, decimal_places=2) 
    stock_minimum = models.PositiveIntegerField(defaul=1) 
    active = models.BooleanField(default=True) 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    created_by = models.CharField(max_length=50) # mientras se usa user
    updated_by = models.CharField(max_length=50) # mientras se usa user
    
    def __str__(self): return f"Variant of {self.product.name} - {self.color} - {self.size}"
    
    class Meta:
       unique_together = ('product', 'gender', 'color', 'size')
       
class MovementInventory(models.Model): 
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='movements') 
    movement_type = models.CharField(max_length=50, choices=[('purchase', 'Purchase'), ('sale', 'Sale'), ('adjustment_positive', 'Adjustment Positive'), ('adjustment_negative', 'Adjustment Negative'), ('return', 'Return')]) 
    quantity = models.PositiveIntegerField()
    observation = models.TextField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True) 
    created_by = models.CharField(max_length=50) 
    
    def __str__(self): return f"Movement of {self.variant.product.name} - {self.movement_type} {self.quantity}"
    
class Sale(models.Model):
    customer = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('canceled', 'Canceled')], default='pending')
    is_order = models.BooleanField(default=False)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    active = models.BooleanField(default=True)
    
    def __str__(self): return f"Sale to {self.customer} - {self.status}"

class SaleDetail(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='details') # por ahora mientras se diseña un cliente
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self): return f"Detail of {self.sales} - {self.variant.product.name} x {self.quantity}"
    
    class Meta:
        unique_together = ('sale', 'variant')
    
