from django import forms

class VideoForm(forms.Form):
    youtube_link = forms.URLField(max_length=247, label=False, widget=forms.URLInput(attrs={'placeholder': 'Enter link here..'}))

