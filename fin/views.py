from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.db import transaction
from .models import Account, Category, Transaction
from .forms import AccountForm, CategoryForm, TransactionForm

# Create your views here.

def account_create(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save()
            messages.success(request, f'Account "{account.name}" has been created!')
            return redirect('fin:transaction_create')
    else:
        form = AccountForm()
    return render(request, 'fin/account_form.html', {'form': form, 'title': 'Create Account'})

def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Category "{category.name}" has been created!')
            return redirect('fin:transaction_create')
    else:
        form = CategoryForm()
    return render(request, 'fin/category_form.html', {'form': form, 'title': 'Create Category'})

def transaction_create(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('account') == 'new':
                return redirect('fin:account_create')
            if form.cleaned_data.get('category') == 'new':
                return redirect('fin:category_create')
            
            try:
                with transaction.atomic():
                    new_transaction = form.save()
                    messages.success(request, f'Transaction recorded successfully! Account balance updated.')
                    return redirect('fin:transaction_create')
            except ValueError as e:
                messages.error(request, str(e))
                return render(request, 'fin/transaction_form.html', {
                    'form': form,
                    'title': 'Record Transaction'
                })
    else:
        form = TransactionForm()
    
    return render(request, 'fin/transaction_form.html', {
        'form': form,
        'title': 'Record Transaction'
    })
