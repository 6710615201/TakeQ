from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from .models import Room, RoomMembership, RoomInvitation, RoomQuizAssignment
from .forms import RoomCreateForm, JoinRoomByCodeForm, InviteForm
from django.contrib import messages
from django.contrib.auth import get_user_model
from myapp.models import Quiz

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
			return redirect('home')
		return render(request, 'room/create_room.html', {'form': form})

class RoomDetailView(LoginRequiredMixin, View):
    def get(self, request, code):
        room = get_object_or_404(Room, code=code)
        role = user_role_in_room(request.user, room)
        members = room.memberships.select_related('user').all()
        assignments = room.assignments.select_related('quiz').all()  

        assigned_quizzes = [a.quiz for a in assignments]

        owner_quizzes = []
        if role in (RoomMembership.ROLE_OWNER, RoomMembership.ROLE_ADMIN):
            owner_quizzes_qs = Quiz.objects.filter(creator=request.user).order_by('-created_at')
            assigned_ids = [q.pk for q in assigned_quizzes]
            owner_quizzes = owner_quizzes_qs.exclude(pk__in=assigned_ids)

        visible_assigned_for_students = [q for q in assigned_quizzes if q.is_published]

        return render(request, 'room/detail.html', {
            'room': room,
            'role': role,
            'members': members,
            'assignments': assignments,
            'assigned_quizzes': assigned_quizzes,
            'owner_quizzes': owner_quizzes,
            'visible_assigned_for_students': visible_assigned_for_students,
        })

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

        if not form.is_valid():
            messages.error(request, "Invalid data")
            return redirect('room:detail', code=room.code)

        username_or_email = form.cleaned_data['username']
        invite_role = form.cleaned_data['role']  # 'admin' or 'student'

        if role == RoomMembership.ROLE_ADMIN and invite_role == 'admin':
            return HttpResponseForbidden()

        try:
            target = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            try:
                target = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                messages.error(request, 'User not found')
                return redirect('room:detail', code=room.code)

        if RoomMembership.objects.filter(room=room, user=target).exists():
            messages.info(request, 'User already a member')
            return redirect('room:detail', code=room.code)

        inv, created = RoomInvitation.objects.get_or_create(
            room=room,
            invited_user=target,
            defaults={'invited_by': request.user, 'role': invite_role}
        )

        if created:
            messages.success(request, f'Invitation sent to {target}')
        else:
            messages.info(request, f'Invitation already exists for {target}')

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
		if role not in (RoomMembership.ROLE_OWNER, RoomMembership.ROLE_ADMIN):
			return HttpResponseForbidden()
		quiz_id = int(request.POST.get('quiz_id'))
		from myapp.models import Quiz
		quiz = Quiz.objects.filter(pk=quiz_id).first()
		if not quiz:
			messages.error(request, 'Quiz not found')
			return redirect('room:detail', code=room.code)
		RoomQuizAssignment.objects.get_or_create(room=room, quiz=quiz, defaults={'assigned_by': request.user})
		return redirect('room:detail', code=room.code)
	
class DeleteRoomView(LoginRequiredMixin, View):
    def post(self, request, code):
        room = get_object_or_404(Room, code=code)
        if room.owner != request.user:
            return HttpResponseForbidden()
        room.delete()
        messages.success(request, 'Room deleted.')
        return redirect('/')  


class ManageMembersView(LoginRequiredMixin, View):
    """
    GET: show members grouped by role, invite form (owner/admin only can invite)
    POST: handle invite (reuses InviteForm logic)
    """
    def get(self, request, code):
        room = get_object_or_404(Room, code=code)
        role = user_role_in_room(request.user, room)

        # Query members and group by role
        members_qs = RoomMembership.objects.filter(room=room).select_related('user').order_by('role', 'user__username')
        owners = [m for m in members_qs if m.role == RoomMembership.ROLE_OWNER]
        admins = [m for m in members_qs if m.role == RoomMembership.ROLE_ADMIN]
        students = [m for m in members_qs if m.role == RoomMembership.ROLE_STUDENT]

        # Invite form (only relevant for owner/admin, but safe to include)
        invite_form = InviteForm()

        return render(request, 'room/manage_members.html', {
            'room': room,
            'role': role,
            'owners': owners,
            'admins': admins,
            'students': students,
            'invite_form': invite_form,
        })

    def post(self, request, code):
        """
        Accept invite submissions from the manage page. Enforce invite permission rules:
        - owner can invite admin or student
        - admin can invite student only
        """
        room = get_object_or_404(Room, code=code)
        role = user_role_in_room(request.user, room)
        if role not in (RoomMembership.ROLE_OWNER, RoomMembership.ROLE_ADMIN):
            return HttpResponseForbidden()

        form = InviteForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Invalid input")
            return redirect('room:manage_members', code=room.code)

        username_or_email = form.cleaned_data['username']
        invite_role = form.cleaned_data['role']  # 'admin' or 'student'

        # Admins cannot invite admins
        if role == RoomMembership.ROLE_ADMIN and invite_role == 'admin':
            return HttpResponseForbidden()

        # find user by username or email
        try:
            target = User.objects.get(username=username_or_email)
        except User.DoesNotExist:
            try:
                target = User.objects.get(email=username_or_email)
            except User.DoesNotExist:
                messages.error(request, 'User not found')
                return redirect('room:manage_members', code=room.code)

        # prevent inviting existing members
        if RoomMembership.objects.filter(room=room, user=target).exists():
            messages.info(request, 'User already a member')
            return redirect('room:manage_members', code=room.code)

        # create invitation
        inv, created = RoomInvitation.objects.get_or_create(
            room=room,
            invited_user=target,
            defaults={'invited_by': request.user, 'role': invite_role}
        )

        if created:
            messages.success(request, f'Invitation sent to {target.username}')
        else:
            messages.info(request, f'Invitation already exists for {target.username}')

        return redirect('room:manage_members', code=room.code)


class RemoveMemberView(LoginRequiredMixin, View):
    """
    POST to remove a member from the room.
    Permission rules:
     - owner may remove admins and students, but not themselves.
     - admin may remove students only.
    """
    def post(self, request, code):
        room = get_object_or_404(Room, code=code)
        role = user_role_in_room(request.user, room)
        if role not in (RoomMembership.ROLE_OWNER, RoomMembership.ROLE_ADMIN):
            return HttpResponseForbidden()

        # member_user_id expected from form
        member_user_id = request.POST.get('member_user_id')
        if not member_user_id:
            messages.error(request, 'Missing member id')
            return redirect('room:manage_members', code=room.code)

        try:
            member_user = User.objects.get(pk=int(member_user_id))
        except User.DoesNotExist:
            messages.error(request, 'User not found')
            return redirect('room:manage_members', code=room.code)

        try:
            membership = RoomMembership.objects.get(room=room, user=member_user)
        except RoomMembership.DoesNotExist:
            messages.error(request, 'User is not a member')
            return redirect('room:manage_members', code=room.code)

        # cannot remove the owner
        if membership.role == RoomMembership.ROLE_OWNER:
            messages.error(request, 'Cannot remove the owner')
            return redirect('room:manage_members', code=room.code)

        # admin can only remove students
        if role == RoomMembership.ROLE_ADMIN and membership.role != RoomMembership.ROLE_STUDENT:
            return HttpResponseForbidden()

        # proceed to delete membership
        membership.delete()
        messages.success(request, f'{member_user.username} removed from the room')
        return redirect('room:manage_members', code=room.code)