from django.shortcuts import render
from django.apps import apps

# Create your views here.
def index(request):
    return render(request,"index.html")

def about(request):
    return render(request,"about.html")

def home(request):
    if request.user.is_authenticated:
        # lazy import to avoid circular imports
        Room = apps.get_model('room', 'Room')
        RoomMembership = apps.get_model('room', 'RoomMembership')
        # rooms where user is owner
        owner_rooms = Room.objects.filter(owner=request.user)
        # rooms where user is admin
        admin_rooms = Room.objects.filter(memberships__user=request.user, memberships__role=RoomMembership.ROLE_ADMIN).distinct()
        # rooms where user is student
        student_rooms = Room.objects.filter(memberships__user=request.user, memberships__role=RoomMembership.ROLE_STUDENT).distinct()
        context = {
            'owner_rooms': owner_rooms,
            'admin_rooms': admin_rooms,
            'student_rooms': student_rooms,
        }
        return render(request, "dashboard.html", context)
    return render(request, "index.html", {})
