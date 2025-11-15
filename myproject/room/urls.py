from django.urls import path
from . import views

app_name = 'room'

urlpatterns = [
	path('create/', views.CreateRoomView.as_view(), name='create'),
	path('detail/<str:code>/', views.RoomDetailView.as_view(), name='detail'),
	path('join/', views.JoinByCodeView.as_view(), name='join_by_code'),
	path('invite/<str:code>/', views.InviteUserView.as_view(), name='invite'),
	path('invitations/', views.InvitationsListView.as_view(), name='invitations'),
	path('invitation/<int:pk>/<str:action>/', views.InvitationResponseView.as_view(), name='invitation_response'),
	path('assign_quiz/<str:code>/', views.AssignQuizToRoomView.as_view(), name='assign_quiz'),
]
