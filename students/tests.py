from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import Course, Student, Subject, UserProfile

User = get_user_model()


class StudentDirectoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="registrar", password="test-password"
        )
        UserProfile.objects.create(user=self.user, role=UserProfile.Role.REGISTRAR)
        self.client.force_login(self.user)
        self.course = Course.objects.create(code="CS", name="Computer Science")
        self.student = Student.objects.create(
            student_id="STU-001",
            first_name="Avery",
            last_name="Morgan",
            email="avery@example.com",
            date_of_birth="2005-04-12",
            course=self.course,
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

        self.assertRedirects(
            response, reverse("students:home"), fetch_redirect_response=False
        )
        self.assertRedirects(
            self.client.get(reverse("students:home")),
            reverse("students:registrar_dashboard"),
        )
        self.assertContains(self.client.get(reverse("students:list")), "Avery Morgan")

    def test_student_can_create_account_for_an_unlinked_record(self):
        self.client.logout()

        response = self.client.post(
            reverse("students:student_register"),
            {
                "student_id": self.student.student_id,
                "email": self.student.email,
                "username": "avery",
                "password1": "Strong-test-password-478!",
                "password2": "Strong-test-password-478!",
            },
        )

        self.assertRedirects(
            response,
            reverse("students:student_dashboard"),
            fetch_redirect_response=False,
        )
        user = User.objects.get(username="avery")
        self.student.refresh_from_db()
        self.assertEqual(self.student.user, user)
        self.assertEqual(user.profile.role, UserProfile.Role.STUDENT)
        self.assertTrue(user.check_password("Strong-test-password-478!"))
        self.assertContains(self.client.get(reverse("students:student_dashboard")), "Avery")

    def test_student_signup_requires_matching_unlinked_record(self):
        self.client.logout()

        response = self.client.post(
            reverse("students:student_register"),
            {
                "student_id": self.student.student_id,
                "email": "wrong@example.com",
                "username": "not-linked",
                "password1": "Strong-test-password-478!",
                "password2": "Strong-test-password-478!",
                "role": UserProfile.Role.REGISTRAR,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="not-linked").exists())
        self.assertContains(response, "No unlinked student record matches")

    def test_registrar_can_create_registrar_and_instructor_accounts(self):
        for username, role in (
            ("new-registrar", UserProfile.Role.REGISTRAR),
            ("new-instructor", UserProfile.Role.INSTRUCTOR),
        ):
            response = self.client.post(
                reverse("students:staff_account_create"),
                {
                    "username": username,
                    "first_name": "New",
                    "last_name": "Staff",
                    "email": f"{username}@example.com",
                    "role": role,
                    "password1": "Strong-test-password-478!",
                    "password2": "Strong-test-password-478!",
                },
            )

            self.assertRedirects(
                response,
                reverse("students:registrar_dashboard"),
                fetch_redirect_response=False,
            )
            account = User.objects.get(username=username)
            self.assertEqual(account.profile.role, role)
            self.assertTrue(account.check_password("Strong-test-password-478!"))

    def test_only_registrars_can_create_staff_accounts(self):
        instructor = User.objects.create_user(username="teacher")
        UserProfile.objects.create(user=instructor, role=UserProfile.Role.INSTRUCTOR)
        self.client.force_login(instructor)

        response = self.client.post(
            reverse("students:staff_account_create"),
            {
                "username": "unauthorized",
                "role": UserProfile.Role.REGISTRAR,
                "password1": "Strong-test-password-478!",
                "password2": "Strong-test-password-478!",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username="unauthorized").exists())

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
                "course": self.course.pk,
                "enrollment_date": "2025-01-15",
            },
        )

        self.assertRedirects(response, reverse("students:list"))
        self.assertTrue(Student.objects.filter(student_id="STU-002").exists())

    def test_registrar_can_link_a_student_account(self):
        student_user = User.objects.create_user(username="jordan")
        UserProfile.objects.create(
            user=student_user, role=UserProfile.Role.STUDENT
        )
        response = self.client.post(
            reverse("students:create"),
            {
                "student_id": "STU-003",
                "first_name": "Jordan",
                "last_name": "Lee",
                "email": "jordan@example.com",
                "date_of_birth": "2004-02-20",
                "gender": "",
                "course": self.course.pk,
                "enrollment_date": "2025-01-15",
                "address": "",
                "user": student_user.pk,
            },
        )

        self.assertRedirects(response, reverse("students:list"))
        self.assertEqual(
            Student.objects.get(student_id="STU-003").user, student_user
        )

    def test_registrar_can_create_courses_and_assign_subjects(self):
        instructor = User.objects.create_user(username="teacher")
        UserProfile.objects.create(
            user=instructor, role=UserProfile.Role.INSTRUCTOR
        )
        response = self.client.post(
            reverse("students:course_create"),
            {"code": "IT", "name": "Information Technology", "description": ""},
        )
        self.assertRedirects(response, reverse("students:courses"))
        course = Course.objects.get(code="IT")

        response = self.client.post(
            reverse("students:subject_create"),
            {
                "code": "IT101",
                "name": "Web Development",
                "course": course.pk,
                "instructors": [instructor.pk],
            },
        )
        self.assertRedirects(response, reverse("students:subjects"))
        subject = Subject.objects.get(code="IT101")
        self.assertEqual(list(subject.instructors.all()), [instructor])

    def test_update_student(self):
        another_course = Course.objects.create(code="DS", name="Data Science")
        response = self.client.post(
            reverse("students:update", args=[self.student.pk]),
            {
                "student_id": "STU-001",
                "first_name": "Avery",
                "last_name": "Morgan",
                "email": "avery@example.com",
                "date_of_birth": "2005-04-12",
                "gender": "",
                "course": another_course.pk,
                "enrollment_date": "2024-09-01",
            },
        )

        self.assertRedirects(response, reverse("students:list"))
        self.student.refresh_from_db()
        self.assertEqual(self.student.course, another_course)

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

    def test_instructor_only_sees_assigned_subject_rosters(self):
        instructor = User.objects.create_user(username="teacher")
        UserProfile.objects.create(
            user=instructor, role=UserProfile.Role.INSTRUCTOR
        )
        subject = Subject.objects.create(
            code="CS101", name="Programming", course=self.course
        )
        subject.instructors.add(instructor)
        self.client.force_login(instructor)

        dashboard = self.client.get(reverse("students:instructor_dashboard"))
        roster = self.client.get(
            reverse("students:instructor_subject", args=[subject.pk])
        )
        registrar_page = self.client.get(reverse("students:list"))

        self.assertContains(dashboard, "Programming")
        self.assertContains(roster, "Avery Morgan")
        self.assertEqual(registrar_page.status_code, 403)

    def test_student_only_sees_own_profile_and_subjects(self):
        student_user = User.objects.create_user(username="learner")
        UserProfile.objects.create(
            user=student_user, role=UserProfile.Role.STUDENT
        )
        Student.objects.create(
            student_id="STU-002",
            first_name="Jordan",
            last_name="Lee",
            email="jordan@example.com",
            date_of_birth="2004-02-20",
            course=self.course,
            enrollment_date="2025-01-15",
            user=student_user,
        )
        Subject.objects.create(
            code="CS101", name="Programming", course=self.course
        )
        self.client.force_login(student_user)

        response = self.client.get(reverse("students:student_dashboard"))

        self.assertContains(response, "Jordan")
        self.assertContains(response, "Programming")
        self.assertEqual(self.client.get(reverse("students:list")).status_code, 403)

    def test_seed_command_creates_requested_roster_and_is_idempotent(self):
        call_command("seed_demo_data", password="Temporary-password-123!")
        call_command("seed_demo_data", password="Another-password-123!")

        self.assertEqual(
            UserProfile.objects.filter(role=UserProfile.Role.REGISTRAR).count(), 2
        )
        self.assertEqual(
            UserProfile.objects.filter(role=UserProfile.Role.INSTRUCTOR).count(), 2
        )
        self.assertEqual(
            UserProfile.objects.filter(role=UserProfile.Role.STUDENT).count(), 10
        )
        self.assertEqual(Course.objects.count(), 10)
        self.assertEqual(Subject.objects.count(), 100)
        self.assertEqual(
            [course.subjects.count() for course in Course.objects.order_by("code")],
            [10] * 10,
        )
