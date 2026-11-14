from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.services import provision_registrar_access
from academics.models import AcademicYear, ClassSection, SectionSubject, Semester
from admissions.models import AdmissionApplication
from attendance.models import AttendanceRecord
from departments.models import Department
from enrollment.models import Enrollment, EnrollmentSubject
from faculty.models import FacultyProfile
from grading.models import Grade, GradeHistory
from students.models import Course, Student, Subject, UserProfile


User = get_user_model()


class AcademicWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(
            code="CST", name="Computing", is_generated=True
        )
        cls.course = Course.objects.create(
            code="BSCS",
            name="Computer Science",
            department=cls.department,
        )
        cls.subject = Subject.objects.create(
            code="CS101", name="Programming", course=cls.course
        )
        cls.academic_year = AcademicYear.objects.create(
            name="2025-2026",
            start_date=date(2025, 6, 1),
            end_date=date(2026, 5, 31),
            is_current=True,
        )
        cls.semester = Semester.objects.create(
            academic_year=cls.academic_year,
            term=Semester.Term.FIRST,
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
        )
        cls.section = ClassSection.objects.create(
            course=cls.course,
            semester=cls.semester,
            name="YEAR1-A",
            year_level=1,
            capacity=1,
        )

        cls.registrar = User.objects.create_user(
            username="registrar", password="test-password"
        )
        UserProfile.objects.create(
            user=cls.registrar, role=UserProfile.Role.REGISTRAR
        )
        provision_registrar_access(cls.registrar)

        cls.instructor = User.objects.create_user(
            username="instructor", password="test-password"
        )
        UserProfile.objects.create(
            user=cls.instructor, role=UserProfile.Role.INSTRUCTOR
        )
        faculty = FacultyProfile.objects.create(
            user=cls.instructor,
            faculty_id="FAC-001",
            department=cls.department,
        )
        cls.class_subject = SectionSubject.objects.create(
            section=cls.section,
            subject=cls.subject,
            instructor=faculty,
        )

        cls.student_user = User.objects.create_user(
            username="student", password="test-password"
        )
        UserProfile.objects.create(
            user=cls.student_user, role=UserProfile.Role.STUDENT
        )
        cls.student = Student.objects.create(
            student_id="STU-001",
            first_name="Jamie",
            last_name="Rivera",
            email="jamie@example.test",
            date_of_birth=date(2005, 1, 1),
            course=cls.course,
            enrollment_date=date(2025, 6, 1),
            user=cls.student_user,
        )
        cls.enrollment = Enrollment.objects.create(
            student=cls.student,
            semester=cls.semester,
            section=cls.section,
            status=Enrollment.Status.APPROVED,
        )
        cls.enrollment_subject = EnrollmentSubject.objects.create(
            enrollment=cls.enrollment,
            class_subject=cls.class_subject,
        )

    def test_admission_approval_creates_linked_student_record(self):
        application = AdmissionApplication.objects.create(
            application_number="ADM-2025-0001",
            first_name="Avery",
            last_name="Morgan",
            email="avery@example.test",
            date_of_birth=date(2006, 3, 5),
            address="Test address",
            preferred_course=self.course,
        )
        self.client.force_login(self.registrar)

        response = self.client.post(
            reverse("admissions:review", args=[application.pk]),
            {"action": "approve", "review_notes": "Documents verified."},
        )

        self.assertRedirects(
            response, reverse("admissions:list"), fetch_redirect_response=False
        )
        application.refresh_from_db()
        self.assertEqual(application.status, AdmissionApplication.Status.APPROVED)
        self.assertEqual(application.student.email, "avery@example.test")
        self.assertEqual(application.student.first_name, "Avery")

    def test_enrollment_capacity_prevents_second_approval(self):
        another_student = Student.objects.create(
            student_id="STU-002",
            first_name="Riley",
            last_name="Cruz",
            email="riley@example.test",
            date_of_birth=date(2005, 2, 1),
            course=self.course,
            enrollment_date=date(2025, 6, 1),
        )
        enrollment = Enrollment.objects.create(
            student=another_student,
            semester=self.semester,
            section=self.section,
        )
        self.client.force_login(self.registrar)

        response = self.client.post(
            reverse("enrollment:decide", args=[enrollment.pk]),
            {"action": "approve"},
        )

        self.assertRedirects(
            response, reverse("enrollment:list"), fetch_redirect_response=False
        )
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, Enrollment.Status.PENDING)

    def test_instructor_grade_edits_are_assigned_and_historized(self):
        self.client.force_login(self.instructor)
        response = self.client.post(
            reverse("grading:update", args=[self.enrollment_subject.pk]),
            {
                "midterm_grade": "80",
                "final_grade": "90",
                "remarks": "Initial grades",
            },
        )
        self.assertRedirects(
            response,
            reverse("grading:roster", args=[self.class_subject.pk]),
            fetch_redirect_response=False,
        )
        grade = Grade.objects.get(enrollment_subject=self.enrollment_subject)
        self.assertEqual(grade.computed_final_grade, Decimal("85"))

        self.client.post(
            reverse("grading:update", args=[self.enrollment_subject.pk]),
            {
                "midterm_grade": "82",
                "final_grade": "92",
                "remarks": "Updated grades",
            },
        )
        self.assertEqual(GradeHistory.objects.filter(grade=grade).count(), 1)

        other_instructor = User.objects.create_user(username="other-instructor")
        UserProfile.objects.create(
            user=other_instructor, role=UserProfile.Role.INSTRUCTOR
        )
        self.client.force_login(other_instructor)
        denied = self.client.get(
            reverse("grading:update", args=[self.enrollment_subject.pk])
        )
        self.assertEqual(denied.status_code, 403)

    def test_instructor_records_attendance_for_assigned_class(self):
        self.client.force_login(self.instructor)
        class_date = timezone.localdate().isoformat()

        response = self.client.post(
            reverse("attendance:mark", args=[self.class_subject.pk]),
            {
                "class_date": class_date,
                f"{self.enrollment_subject.pk}-status": AttendanceRecord.Status.PRESENT,
                f"{self.enrollment_subject.pk}-notes": "On time",
            },
        )

        self.assertRedirects(
            response,
            reverse("attendance:mark", args=[self.class_subject.pk]),
            fetch_redirect_response=False,
        )
        record = AttendanceRecord.objects.get(
            enrollment_subject=self.enrollment_subject,
            class_date=timezone.localdate(),
        )
        self.assertEqual(record.status, AttendanceRecord.Status.PRESENT)
        self.assertEqual(record.marked_by, self.instructor)

    def test_registrar_admin_permissions_exclude_auth_user_management(self):
        self.assertTrue(self.registrar.is_staff)
        self.assertTrue(self.registrar.has_perm("academics.add_classsection"))
        self.assertFalse(self.registrar.has_perm("auth.add_user"))

    def test_registrar_can_export_reports_but_instructors_cannot(self):
        self.client.force_login(self.registrar)
        report_page = self.client.get(reverse("students:reports"))
        export = self.client.get(
            reverse("students:report_export", args=["students"])
        )

        self.assertEqual(report_page.status_code, 200)
        self.assertEqual(export["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(b"STU-001", export.content)

        Grade.objects.create(
            enrollment_subject=self.enrollment_subject,
            midterm_grade=Decimal("78"),
            final_grade=Decimal("82"),
        )
        AttendanceRecord.objects.create(
            enrollment_subject=self.enrollment_subject,
            class_date=timezone.localdate(),
            status=AttendanceRecord.Status.PRESENT,
        )
        expected_report_content = {
            "enrollments": b"STU-001",
            "grades": b"Programming",
            "attendance": b"Programming",
        }
        for report_type, expected_content in expected_report_content.items():
            export = self.client.get(
                reverse("students:report_export", args=[report_type])
            )
            self.assertEqual(export.status_code, 200)
            self.assertIn(expected_content, export.content)

        self.client.force_login(self.instructor)
        denied = self.client.get(
            reverse("students:report_export", args=["students"])
        )
        self.assertEqual(denied.status_code, 403)
