from django import forms
from .models import Room

class RoomCreateForm(forms.ModelForm):
	class Meta:
		model = Room
		fields = ['name','description']

class JoinRoomByCodeForm(forms.Form):
	code = forms.CharField(max_length=12)

class InviteForm(forms.Form):
	username = forms.CharField(max_length=150, help_text='Username or email of user to invite')
	role = forms.ChoiceField(choices=[('student','Student'),('admin','Admin')])
