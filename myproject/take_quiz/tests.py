from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from myapp.models import Quiz, Question, Choice, Attempt, Answer

User = get_user_model()

class TakeQuizFlowTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(username="teacher", password="teachpw")
        self.student = User.objects.create_user(username="student", password="studpw")
        self.other_student = User.objects.create_user(username="other", password="otherpw")

        self.quiz = Quiz.objects.create(
            title="Sample Quiz",
            description="For testing",
            creator=self.teacher,
            is_published=True
        )

        self.q_mcq = Question.objects.create(quiz=self.quiz, text="2 + 2 = ?", qtype="mcq", order=1)
        self.c_wrong = Choice.objects.create(question=self.q_mcq, text="3", is_correct=False)
        self.c_right = Choice.objects.create(question=self.q_mcq, text="4", is_correct=True)

        self.q_short = Question.objects.create(quiz=self.quiz, text="Explain 2+2", qtype="short", order=2)

        self.client = Client()

    def test_happy_path_start_take_submit_and_result(self):
        logged_in = self.client.login(username="student", password="studpw")
        self.assertTrue(logged_in)

        list_url = reverse("take_quiz:quiz_list")
        r = self.client.get(list_url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.quiz.title)

        start_url = reverse("take_quiz:start_quiz", args=[self.quiz.id])
        r2 = self.client.get(start_url)
        self.assertEqual(r2.status_code, 302)
        take_url = r2.url

        r3 = self.client.get(take_url)
        self.assertEqual(r3.status_code, 200)
        self.assertContains(r3, self.q_mcq.text)
        self.assertContains(r3, self.q_short.text)

        import re
        m = re.search(r'/take/\d+/take/(\d+)/', take_url)
        self.assertIsNotNone(m)
        attempt_id = int(m.group(1))

        submit_url = reverse("take_quiz:submit_quiz", args=[attempt_id])
        post_data = {
            f"question_{self.q_mcq.id}": str(self.c_right.id),
            f"question_{self.q_short.id}": "Because 2+2 equals 4"
        }
        resp = self.client.post(submit_url, post_data)
        self.assertEqual(resp.status_code, 302)
        result_url = resp.url

        attempt = Attempt.objects.get(pk=attempt_id)
        self.assertIsNotNone(attempt.finished_at)
        self.assertAlmostEqual(attempt.score, 100.0, places=3)

        answers = attempt.answers.all()
        self.assertEqual(answers.count(), 2)
        rres = self.client.get(result_url)
        self.assertEqual(rres.status_code, 200)
        self.assertContains(rres, "Score")

    def test_sad_paths_and_edge_cases(self):
        self.client.logout()
        login_url = reverse("login") 
        list_url = reverse("take_quiz:quiz_list")
        start_url = reverse("take_quiz:start_quiz", args=[self.quiz.id])

        r = self.client.get(list_url)
        self.assertEqual(r.status_code, 302)
        self.assertIn(login_url, r.url)

        r2 = self.client.get(start_url)
        self.assertEqual(r2.status_code, 302)
        self.assertIn(login_url, r2.url)

        self.client.login(username="student", password="studpw")
        rstart = self.client.get(start_url)
        self.assertEqual(rstart.status_code, 302)
        import re
        m = re.search(r'/take/\d+/take/(\d+)/', rstart.url)
        attempt_id = int(m.group(1))

        submit_url = reverse("take_quiz:submit_quiz", args=[attempt_id])
        rget = self.client.get(submit_url)
        self.assertEqual(rget.status_code, 302)
        home_url = reverse("home")
        self.assertIn(home_url, rget.url)

        post_data_invalid = {
            f"question_{self.q_mcq.id}": "999999",
            f"question_{self.q_short.id}": "some text"
        }
        rpost = self.client.post(submit_url, post_data_invalid)
        self.assertEqual(rpost.status_code, 302)
        att = Attempt.objects.get(pk=attempt_id)
        self.assertAlmostEqual(att.score, 0.0, places=3)

        rstart2 = self.client.get(start_url)
        m2 = re.search(r'/take/\d+/take/(\d+)/', rstart2.url)
        attempt_id2 = int(m2.group(1))
        self.client.logout()
        self.client.login(username="other", password="otherpw")
        submit_other_url = reverse("take_quiz:submit_quiz", args=[attempt_id2])
        r_other = self.client.post(submit_other_url, {
            f"question_{self.q_mcq.id}": str(self.c_right.id),
            f"question_{self.q_short.id}": "answer"
        })
        self.assertEqual(r_other.status_code, 404)
