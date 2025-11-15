from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from .models import Room, RoomMembership, RoomInvitation, RoomQuizAssignment
from .forms import RoomCreateForm, JoinRoomByCodeForm, InviteForm
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

def user_role_in_room(user, room):
	try:
		m = RoomMembership.objects.get(user=user, room=room)
		return m.role
	except RoomMembership.DoesNotExist:
		return None

class CreateRoomView(LoginRequiredMixin, View):
	def get(self, request):
		form = RoomCreateForm()
		return render(request, 'room/create_room.html', {'form': form})

	def post(self, request):
		form = RoomCreateForm(request.POST)
		if form.is_valid():
			room = form.save(commit=False)
			room.owner = request.user
			room.save()
			RoomMembership.objects.create(room=room, user=request.user, role=RoomMembership.ROLE_OWNER)
			return redirect('room:detail', code=room.code)
		return render(request, 'room/create_room.html', {'form': form})

class RoomDetailView(LoginRequiredMixin, View):
	def get(self, request, code):
		room = get_object_or_404(Room, code=code)
		role = user_role_in_room(request.user, room)
		members = room.memberships.select_related('user').all()
		assignments = room.assignments.select_related('quiz').all()
		return render(request, 'room/detail.html', {'room': room, 'role': role, 'members': members, 'assignments': assignments})

class JoinByCodeView(LoginRequiredMixin, View):
	def post(self, request):
		form = JoinRoomByCodeForm(request.POST)
		if not form.is_valid():
			return redirect('/')
		code = form.cleaned_data['code'].upper()
		room = get_object_or_404(Room, code=code)
		if RoomMembership.objects.filter(room=room, user=request.user).exists():
			return redirect('room:detail', code=room.code)
		RoomMembership.objects.create(room=room, user=request.user, role=RoomMembership.ROLE_STUDENT)
		return redirect('room:detail', code=room.code)

class InviteUserView(LoginRequiredMixin, View):
	def post(self, request, code):
		form = InviteForm(request.POST)
		room = get_object_or_404(Room, code=code)
		role = user_role_in_room(request.user, room)
		if role not in (RoomMembership.ROLE_OWNER, RoomMembership.ROLE_ADMIN):
			return HttpResponseForbidden()
		if form.is_valid():
			username = form.cleaned_data['username']
			invite_role = form.cleaned_data['role']
			if role == RoomMembership.ROLE_ADMIN and invite_role == 'admin':
				return HttpResponseForbidden()
			# find user by username or email
			try:
				target = User.objects.get(username=username)
			except User.DoesNotExist:
				try:
					target = User.objects.get(email=username)
				except User.DoesNotExist:
					messages.error(request, 'User not found')
					return redirect('room:detail', code=room.code)
			if RoomMembership.objects.filter(room=room, user=target).exists():
				messages.info(request, 'User already member')
				return redirect('room:detail', code=room.code)
			inv, created = RoomInvitation.objects.get_or_create(
				room=room, invited_user=target,
				defaults={'invited_by': request.user, 'role': invite_role}
			)
			if not created:
				if inv.status == RoomInvitation.STATUS_PENDING:
					messages.info(request, 'Invitation already pending')
				else:
					inv.status = RoomInvitation.STATUS_PENDING
					inv.invited_by = request.user
					inv.role = invite_role
					inv.save()
			return redirect('room:invitations')
		return redirect('room:detail', code=room.code)

class InvitationResponseView(LoginRequiredMixin, View):
	def post(self, request, pk, action):
		inv = get_object_or_404(RoomInvitation, pk=pk, invited_user=request.user)
		if inv.status != RoomInvitation.STATUS_PENDING:
			return redirect('room:invitations')
		if action == 'accept':
			inv.accept()
		else:
			inv.decline()
		return redirect('room:invitations')

class InvitationsListView(LoginRequiredMixin, View):
	def get(self, request):
		invs = RoomInvitation.objects.filter(invited_user=request.user).order_by('-created_at')
		return render(request, 'room/invitations_list.html', {'invitations': invs})

class AssignQuizToRoomView(LoginRequiredMixin, View):
	def post(self, request, code):
		room = get_object_or_404(Room, code=code)
		role = user_role_in_room(request.user, room)
		if role != RoomMembership.ROLE_OWNER:
			return HttpResponseForbidden()
		quiz_id = int(request.POST.get('quiz_id'))
		from myapp.models import Quiz
		quiz = Quiz.objects.filter(pk=quiz_id).first()
		if not quiz:
			messages.error(request, 'Quiz not found')
			return redirect('room:detail', code=room.code)
		RoomQuizAssignment.objects.get_or_create(room=room, quiz=quiz, defaults={'assigned_by': request.user})
		return redirect('room:detail', code=room.code)
