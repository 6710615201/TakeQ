from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, tag
from django.urls import reverse
from django.utils import timezone

from myapp.models import Quiz, Question, Choice, Attempt

User = get_user_model()


@tag("student")
class StudentQuizTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.student = User.objects.create_user(username="student", password="password")
        self.teacher = User.objects.create_user(username="teacher", password="password")

        self.quiz = Quiz.objects.create(
            title="Math Quiz",
            creator=self.teacher,
            is_published=True,
            time_limit_minutes=10,
        )

        self.question = Question.objects.create(
            quiz=self.quiz,
            text="1+1=?",
            qtype="mcq",
            order=1,
        )

        self.correct = Choice.objects.create(
            question=self.question,
            text="2",
            is_correct=True,
        )
        self.wrong = Choice.objects.create(
            question=self.question,
            text="3",
            is_correct=False,
        )

    def test_student_gets_full_score(self):
        self.client.login(username="student", password="password")

        attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
        )

        url = reverse("take_quiz:submit_quiz", args=[attempt.id])
        self.client.post(url, {
            f"question_{self.question.id}": self.correct.id
        })

        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 100.0)

    def test_student_gets_zero_score(self):
        self.client.login(username="student", password="password")

        attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
        )

        url = reverse("take_quiz:submit_quiz", args=[attempt.id])
        self.client.post(url, {
            f"question_{self.question.id}": self.wrong.id
        })

        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 0.0)

    def test_student_cannot_view_others_attempt(self):
        hacker = User.objects.create_user(username="hacker", password="password")
        self.client.login(username="hacker", password="password")

        attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
        )

        url = reverse("take_quiz:attempt_result", args=[attempt.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_manual_submit_time_exceeded(self):
        self.client.login(username="student", password="password")

        attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
        )
        attempt.started_at = timezone.now() - timedelta(minutes=20)
        attempt.save(update_fields=["started_at"])

        url = reverse("take_quiz:submit_quiz", args=[attempt.id])
        self.client.post(url, {
            f"question_{self.question.id}": self.correct.id
        })

        attempt.refresh_from_db()
        self.assertIsNone(attempt.score)

    def test_auto_submit_time_exceeded_allowed(self):
        self.client.login(username="student", password="password")

        attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
        )
        attempt.started_at = timezone.now() - timedelta(minutes=20)
        attempt.save(update_fields=["started_at"])

        url = reverse("take_quiz:submit_quiz", args=[attempt.id])
        self.client.post(url, {
            f"question_{self.question.id}": self.correct.id,
            "auto_submitted": "true",
        })

        attempt.refresh_from_db()
        self.assertEqual(attempt.score, 100.0)

    def test_mixed_question_types_no_immediate_score(self):
        """
        Scenario: มี Short Answer ผสม → ยังไม่แสดงคะแนนเป็น %
        """
        q_short = Question.objects.create(
            quiz=self.quiz,
            text="Name a color",
            qtype="short",
            order=2,
        )

        self.client.login(username="student", password="password")

        attempt = Attempt.objects.create(
            quiz=self.quiz,
            taker=self.student,
        )

        submit_url = reverse("take_quiz:submit_quiz", args=[attempt.id])
        self.client.post(
            submit_url,
            {
                f"question_{self.question.id}": self.correct.id,
                f"question_{q_short.id}": "Blue",
            },
        )

        result_url = reverse("take_quiz:attempt_result", args=[attempt.id])
        response = self.client.get(result_url)

        self.assertEqual(response.status_code, 200)

        
        self.assertNotContains(response, "%")

        
        self.assertContains(response, "Not available")
        self.assertContains(response, "รอการตรวจ")
