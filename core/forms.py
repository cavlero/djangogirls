from django import forms

class SearchForm(forms.Form):
    search = forms.CharField(
        max_length=100, 
        required=False, 
        label="Search for recipes",
        widget=forms.TextInput(attrs={'size': '20'})  # Set the size here
    )
