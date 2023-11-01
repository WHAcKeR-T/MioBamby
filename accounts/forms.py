# forms.py

from django import forms
from multiupload.fields import MultiFileField

class ArticleForm(forms.Form):
    Ref = forms.CharField(max_length=100, required=False)
    Couleur = forms.CharField(max_length=7, required=True, widget=forms.TextInput(attrs={'type': 'color'}))
    PrixU = forms.DecimalField(required=True, label="PrixU")
    Images = MultiFileField(max_file_size=10 * 1024 * 1024, min_num=1, max_num=5)
    Couleurs = forms.CharField(widget=forms.HiddenInput(), required=False)  # Hidden field for storing colors as JSON
    Taille = forms.CharField(max_length=10, required=True)
    Tailles = forms.CharField(widget=forms.HiddenInput(), required=False)