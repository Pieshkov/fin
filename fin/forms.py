from django import forms
from .models import Account, Category, Transaction

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name', 'account_type', 'currency']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_type': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
        }

class CategoryForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=Category.objects.filter(parent__isnull=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="No parent (Create as main category)"
    )

    class Meta:
        model = Category
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
        }

class TransactionForm(forms.ModelForm):
    new_account = forms.BooleanField(required=False, widget=forms.HiddenInput())
    
    class Meta:
        model = Transaction
        fields = ['date', 'transaction_type', 'amount', 'account', 'currency', 'category', 'comment']
        widgets = {
            'date': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'transaction_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'account': forms.Select(attrs={'class': 'form-control'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={
                'class': 'form-control select2',
                'data-placeholder': 'Select a category'
            }),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].initial = timezone.now()
        self.fields['category'].queryset = Category.objects.all()
        self.fields['account'].queryset = Account.objects.all()
        
        # Add "Create new" options
        account_choices = list(self.fields['account'].choices)
        account_choices.append(('new', '➕ Create new account'))
        self.fields['account'].choices = account_choices
        
        category_choices = list(self.fields['category'].choices)
        category_choices.append(('new', '➕ Create new category'))
        self.fields['category'].choices = category_choices
