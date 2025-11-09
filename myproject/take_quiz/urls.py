from django.urls import path
from . import views

app_name = "take_quiz"

urlpatterns = [
    path("", views.QuizListView.as_view(), name="quiz_list"),
    path("<int:quiz_id>/start/", views.start_quiz, name="start_quiz"),
    path("<int:quiz_id>/take/<int:attempt_id>/", views.take_quiz, name="take_quiz"),
    path("<int:attempt_id>/submit/", views.submit_quiz, name="submit_quiz"),
    path("attempt/<int:attempt_id>/result/", views.attempt_result, name="attempt_result"),
]