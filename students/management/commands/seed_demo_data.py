import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from students.models import Course, Student, Subject, UserProfile


COURSES = [
    ("BSCS", "Computer Science"),
    ("BSIT", "Information Technology"),
    ("BSBA", "Business Administration"),
]

SUBJECTS = [
    ("CS101", "Programming Fundamentals", "BSCS", "demo_instructor1"),
    ("CS102", "Database Systems", "BSCS", "demo_instructor1"),
    ("CS103", "Computer Networks", "BSCS", "demo_instructor2"),
    ("IT201", "Web Development", "BSIT", "demo_instructor1"),
    ("IT202", "Cybersecurity", "BSIT", "demo_instructor2"),
    ("IT203", "Systems Administration", "BSIT", "demo_instructor2"),
    ("BA101", "Principles of Management", "BSBA", "demo_instructor1"),
    ("BA102", "Financial Accounting", "BSBA", "demo_instructor2"),
    ("BA103", "Marketing Principles", "BSBA", "demo_instructor2"),
]

PEOPLE = [
    ("demo_registrar", "Alex", "Rivera", "registrar@example.test", "registrar"),
    ("demo_instructor1", "Taylor", "Brooks", "instructor1@example.test", "instructor"),
    ("demo_instructor2", "Morgan", "Reed", "instructor2@example.test", "instructor"),
    ("demo_student01", "Jamie", "Cruz", "student01@example.test", "student"),
    ("demo_student02", "Riley", "Flores", "student02@example.test", "student"),
    ("demo_student03", "Casey", "Santos", "student03@example.test", "student"),
    ("demo_student04", "Jordan", "Garcia", "student04@example.test", "student"),
    ("demo_student05", "Avery", "Mendoza", "student05@example.test", "student"),
    ("demo_student06", "Quinn", "Torres", "student06@example.test", "student"),
    ("demo_student07", "Drew", "Bautista", "student07@example.test", "student"),
    ("demo_student08", "Skyler", "Reyes", "student08@example.test", "student"),
    ("demo_student09", "Parker", "Castillo", "student09@example.test", "student"),
    ("demo_student10", "Robin", "Diaz", "student10@example.test", "student"),
]

STUDENTS = [
    ("STU-2025-001", "demo_student01", "BSCS"),
    ("STU-2025-002", "demo_student02", "BSCS"),
    ("STU-2025-003", "demo_student03", "BSCS"),
    ("STU-2025-004", "demo_student04", "BSCS"),
    ("STU-2025-005", "demo_student05", "BSIT"),
    ("STU-2025-006", "demo_student06", "BSIT"),
    ("STU-2025-007", "demo_student07", "BSIT"),
    ("STU-2025-008", "demo_student08", "BSBA"),
    ("STU-2025-009", "demo_student09", "BSBA"),
    ("STU-2025-010", "demo_student10", "BSBA"),
]


class Command(BaseCommand):
    help = "Create a sample registrar, instructors, students, courses, and subjects."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Set the same initial password for newly created demo accounts.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user_model = get_user_model()
        created_credentials = []
        users = {}

        for username, first_name, last_name, email, role in PEOPLE:
            user, created = user_model.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
            )
            if created:
                password = options["password"] or secrets.token_urlsafe(24)
                user.set_password(password)
                user.save(update_fields=["password"])
                created_credentials.append((username, password))
            elif UserProfile.objects.filter(user=user).exclude(role=role).exists():
                raise CommandError(
                    f"Existing account {username!r} already has a different role."
                )
            UserProfile.objects.get_or_create(user=user, defaults={"role": role})
            users[username] = user

        courses = {}
        for code, name in COURSES:
            course = Course.objects.filter(code=code).first()
            if course is None:
                course = Course.objects.filter(name=name).first()
            if course is None:
                course = Course.objects.create(code=code, name=name)
            elif course.name != name and course.code == code:
                raise CommandError(
                    f"Course code {code!r} already belongs to {course.name!r}."
                )
            courses[code] = course

        for code, name, course_code, instructor_username in SUBJECTS:
            subject, _ = Subject.objects.get_or_create(
                code=code,
                defaults={"name": name, "course": courses[course_code]},
            )
            if subject.name != name or subject.course_id != courses[course_code].pk:
                raise CommandError(
                    f"Subject code {code!r} already belongs to another subject."
                )
            subject.instructors.add(users[instructor_username])

        for index, (student_id, username, course_code) in enumerate(STUDENTS, start=1):
            user = users[username]
            student, _ = Student.objects.get_or_create(
                student_id=student_id,
                defaults={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "date_of_birth": f"{2004 + index % 3:04d}-{1 + index % 12:02d}-15",
                    "course": courses[course_code],
                    "enrollment_date": "2025-09-01",
                    "user": user,
                },
            )
            if student.user_id not in (None, user.pk):
                raise CommandError(
                    f"Student ID {student_id!r} is already linked to another account."
                )
            if student.user_id is None:
                student.user = user
                student.save(update_fields=["user"])
            UserProfile.objects.get_or_create(
                user=user, defaults={"role": UserProfile.Role.STUDENT}
            )

        self.stdout.write(self.style.SUCCESS("Demo academic data is ready."))
        self.stdout.write("Accounts: 1 registrar, 2 instructors, and 10 students.")
        if created_credentials:
            self.stdout.write(
                self.style.WARNING(
                    "Save these one-time demo credentials now; they are not shown again."
                )
            )
            for username, password in created_credentials:
                self.stdout.write(f"{username}: {password}")
        else:
            self.stdout.write("No accounts were created; existing passwords were unchanged.")
