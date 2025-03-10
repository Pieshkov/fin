from django.db import models
from django.utils import timezone
from django.db import transaction

# Create your models here.

class Account(models.Model):
    CURRENCY_CHOICES = [
        ('EUR', 'Euro'),
        ('USD', 'US Dollar'),
        ('UAH', 'Ukrainian Hryvnia'),
    ]
    
    ACCOUNT_TYPES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('SAVINGS', 'Savings'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_currency_display()})"

class Category(models.Model):
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='subcategories')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    class Meta:
        verbose_name_plural = "Categories"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('TRANSFER', 'Transfer'),
    ]
    
    date = models.DateTimeField(default=timezone.now)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    currency = models.CharField(max_length=3, choices=Account.CURRENCY_CHOICES)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.amount} {self.currency} ({self.date.strftime('%Y-%m-%d')})"
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only for new transactions
            with transaction.atomic():
                if self.transaction_type == 'INCOME':
                    self.account.balance += self.amount
                elif self.transaction_type == 'EXPENSE':
                    if self.account.balance < self.amount:
                        raise ValueError(f'Insufficient funds in {self.account.name}')
                    self.account.balance -= self.amount
                self.account.save()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)
