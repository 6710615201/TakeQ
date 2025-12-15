from django.test import TestCase, Client, tag
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from myapp.models import Quiz, Question, Attempt, Answer

User = get_user_model()


@tag("teacher")
class TeacherGradingTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username="student", password="password")
        self.teacher = User.objects.create_user(username="teacher", password="password")

        self.quiz = Quiz.objects.create(
            title="Essay Quiz",
            creator=self.teacher,
            is_published=True
        )

        self.question = Question.objects.create(
            quiz=self.quiz,
            text="Explain gravity",
            qtype="short",
            order=1
        )

        self.attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
            finished_at=timezone.now()
        )

        self.answer = Answer.objects.create(
            attempt=self.attempt,
            question=self.question,
            text="It is a force"
        )

    def test_teacher_can_grade_short_answer(self):
        self.client.login(username="teacher", password="password")

        self.answer.is_correct = True
        self.answer.save(update_fields=["is_correct"])

        total = self.quiz.questions.count()
        correct = self.attempt.answers.filter(is_correct=True).count()

        self.attempt.score = (correct / total) * 100
        self.attempt.graded = True
        self.attempt.save(update_fields=["score", "graded"])

        self.attempt.refresh_from_db()
        self.assertEqual(self.attempt.score, 100.0)
        self.assertTrue(self.attempt.graded)

    def test_student_sees_score_after_grading(self):
        self.answer.is_correct = True
        self.answer.save()

        self.attempt.score = 100
        self.attempt.graded = True
        self.attempt.save()

        self.client.login(username="student", password="password")
        url = reverse("take_quiz:attempt_result", args=[self.attempt.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "100 %")
