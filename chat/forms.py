from django import forms
from .models import Room

class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ["name"]
        widgets = {"name": forms.TextInput(
            attrs={"class": "form-control", "placeholder": "聊天室名称"})} 