from django.contrib import admin
from .models import Room, RoomMembership, RoomInvitation, RoomQuizAssignment

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = ('name','code','owner','created_at')
	search_fields = ('name','code','owner__username')

@admin.register(RoomMembership)
class RoomMembershipAdmin(admin.ModelAdmin):
	list_display = ('room','user','role','joined_at')
	list_filter = ('role',)

@admin.register(RoomInvitation)
class RoomInvitationAdmin(admin.ModelAdmin):
	list_display = ('room','invited_user','role','status','created_at','responded_at')
	list_filter = ('status','role')

@admin.register(RoomQuizAssignment)
class RoomQuizAssignmentAdmin(admin.ModelAdmin):
	list_display = ('room','quiz_title','assigned_at','assigned_by')

	@admin.display(description='Quiz')
	def quiz_title(self, obj):
		q = obj.get_quiz() if hasattr(obj, 'get_quiz') else None
		return q.title if q else f"(id:{getattr(obj, 'quiz_id', '?')})"

