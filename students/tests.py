from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Student

User = get_user_model()


class StudentDirectoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="registrar", password="test-password"
        )
        self.client.force_login(self.user)
        self.student = Student.objects.create(
            student_id="STU-001",
            first_name="Avery",
            last_name="Morgan",
            email="avery@example.com",
            date_of_birth="2005-04-12",
            course="Computer Science",
            enrollment_date="2024-09-01",
        )

    def test_anonymous_users_cannot_access_student_records(self):
        self.client.logout()

        response = self.client.get(reverse("students:list"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('students:list')}",
            fetch_redirect_response=False,
        )
        self.assertEqual(Student.objects.count(), 1)

    def test_user_can_sign_in(self):
        self.client.logout()

        response = self.client.post(
            reverse("login"),
            {"username": "registrar", "password": "test-password"},
        )

        self.assertRedirects(response, reverse("students:list"))
        self.assertContains(self.client.get(reverse("students:list")), "Avery Morgan")

    def test_directory_shows_students_and_summary(self):
        response = self.client.get(reverse("students:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Avery Morgan")
        self.assertContains(response, "STU-001")
        self.assertContains(response, "Computer Science")

    def test_directory_searches_across_student_fields(self):
        response = self.client.get(reverse("students:list"), {"q": "Computer"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Avery Morgan")

        response = self.client.get(reverse("students:list"), {"q": "not-found"})
        self.assertContains(response, "No matching students")

    def test_create_student(self):
        response = self.client.post(
            reverse("students:create"),
            {
                "student_id": "STU-002",
                "first_name": "Jordan",
                "last_name": "Lee",
                "email": "jordan@example.com",
                "date_of_birth": "2004-02-20",
                "gender": "P",
                "course": "Mathematics",
                "enrollment_date": "2025-01-15",
            },
        )

        self.assertRedirects(response, reverse("students:list"))
        self.assertTrue(Student.objects.filter(student_id="STU-002").exists())

    def test_update_student(self):
        response = self.client.post(
            reverse("students:update", args=[self.student.pk]),
            {
                "student_id": "STU-001",
                "first_name": "Avery",
                "last_name": "Morgan",
                "email": "avery@example.com",
                "date_of_birth": "2005-04-12",
                "gender": "",
                "course": "Data Science",
                "enrollment_date": "2024-09-01",
            },
        )

        self.assertRedirects(response, reverse("students:list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.course, "Data Science")

    def test_delete_requires_post_confirmation(self):
        confirmation = self.client.get(
            reverse("students:delete", args=[self.student.pk])
        )
        self.assertEqual(confirmation.status_code, 200)
        self.assertTrue(Student.objects.filter(pk=self.student.pk).exists())

        response = self.client.post(
            reverse("students:delete", args=[self.student.pk])
        )
        self.assertRedirects(response, reverse("students:list"))
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
