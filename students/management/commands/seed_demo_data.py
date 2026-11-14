import secrets
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.services import provision_registrar_access
from academics.models import (
    AcademicYear,
    ClassSchedule,
    ClassSection,
    Curriculum,
    CurriculumSubject,
    SectionSubject,
    Semester,
)
from attendance.models import AttendanceRecord
from admissions.models import AdmissionApplication, AdmissionDocument
from audit_logs.models import AuditLog
from departments.models import Department
from documents.models import StudentDocument
from enrollment.models import Enrollment, EnrollmentSubject
from faculty.models import FacultyProfile
from grading.models import Grade
from students.models import Course, Student, Subject, UserProfile


COURSES = [
    ("BSCS", "Computer Science"),
    ("BSIT", "Information Technology"),
    ("BSBA", "Business Administration"),
    ("BSN", "Nursing"),
    ("BSED", "Secondary Education"),
    ("BEED", "Elementary Education"),
    ("BSHM", "Hospitality Management"),
    ("BSTM", "Tourism Management"),
    ("BSCRIM", "Criminology"),
    ("BSECE", "Electronics Engineering"),
]

COURSE_DEPARTMENTS = {
    "BSCS": "CST",
    "BSIT": "CST",
    "BSBA": "BUS",
    "BSN": "HSC",
    "BSED": "EDU",
    "BEED": "EDU",
    "BSHM": "HOS",
    "BSTM": "TOU",
    "BSCRIM": "CRJ",
    "BSECE": "ENG",
}

DEPARTMENTS = [
    ("CST", "Computing and Information Technology"),
    ("BUS", "Business and Management"),
    ("HSC", "Health Sciences"),
    ("EDU", "Education"),
    ("HOS", "Hospitality Management"),
    ("TOU", "Tourism Management"),
    ("CRJ", "Criminal Justice"),
    ("ENG", "Engineering"),
]

COURSE_SUBJECTS = [
    ("BSCS", "CS1", [
        "Programming Fundamentals", "Database Systems", "Computer Networks",
        "Data Structures", "Operating Systems", "Software Engineering",
        "Web Development", "Cybersecurity", "Artificial Intelligence",
        "Systems Analysis and Design",
    ]),
    ("BSIT", "IT2", [
        "Web Development", "Cybersecurity", "Systems Administration",
        "Database Management", "Networking Fundamentals", "IT Project Management",
        "Cloud Computing", "Human-Computer Interaction", "Mobile App Development",
        "Information Assurance",
    ]),
    ("BSBA", "BA1", [
        "Principles of Management", "Financial Accounting", "Marketing Principles",
        "Business Communication", "Human Resource Management", "Business Finance",
        "Operations Management", "Entrepreneurship", "Business Law",
        "Strategic Management",
    ]),
    ("BSN", "NUR", [
        "Fundamentals of Nursing", "Anatomy and Physiology", "Health Assessment",
        "Nursing Informatics", "Pharmacology", "Community Health Nursing",
        "Maternal and Child Nursing", "Medical-Surgical Nursing",
        "Mental Health Nursing", "Nursing Research",
    ]),
    ("BSED", "SED", [
        "Foundations of Education", "Educational Psychology", "Curriculum Development",
        "Assessment of Learning", "Teaching Strategies", "Classroom Management",
        "Inclusive Education", "Instructional Technology", "Research in Education",
        "Practice Teaching",
    ]),
    ("BEED", "EED", [
        "Child and Adolescent Development", "Principles of Teaching",
        "Teaching Reading", "Teaching Mathematics", "Teaching Science",
        "Teaching Social Studies", "Assessment in Elementary Education",
        "Educational Technology", "Inclusive Classroom Practices",
        "Practice Teaching",
    ]),
    ("BSHM", "HM", [
        "Introduction to Hospitality", "Food and Beverage Service",
        "Front Office Operations", "Housekeeping Management",
        "Food Safety and Sanitation", "Hospitality Marketing",
        "Culinary Fundamentals", "Event Management", "Hospitality Accounting",
        "Hotel Operations",
    ]),
    ("BSTM", "TM", [
        "Introduction to Tourism", "Tourism Planning and Development",
        "Travel Agency Operations", "Tour Guiding", "Tourism Marketing",
        "Airline Operations", "Sustainable Tourism", "Event and Convention Management",
        "Tourism Geography", "Tourism Research",
    ]),
    ("BSCRIM", "CRIM", [
        "Introduction to Criminology", "Criminal Law", "Police Organization",
        "Criminal Investigation", "Forensic Science", "Criminal Sociology",
        "Correctional Administration", "Victimology", "Ethics in Criminal Justice",
        "Criminal Justice Research",
    ]),
    ("BSECE", "ECE", [
        "Circuit Analysis", "Digital Systems Design", "Electronic Devices",
        "Signals and Systems", "Microprocessor Systems", "Communication Systems",
        "Control Systems", "Electromagnetics", "Engineering Mathematics",
        "Electronics Design Project",
    ]),
]

SUBJECTS = [
    (
        f"{prefix}{index:02d}",
        name,
        course_code,
        "demo_instructor1" if index % 2 else "demo_instructor2",
    )
    for course_code, prefix, names in COURSE_SUBJECTS
    for index, name in enumerate(names, start=1)
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


def build_sample_pdf():
    stream = (
        b"BT /F1 16 Tf 50 750 Td (DEMO SAMPLE - NOT OFFICIAL) Tj "
        b"0 -28 Td /F1 11 Tf (Generated example document for testing only.) Tj ET"
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        ),
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return bytes(pdf)


class Command(BaseCommand):
    help = "Provision generated starter accounts and academic records."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            help="Set the same initial password for newly created accounts.",
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
            if role == UserProfile.Role.REGISTRAR:
                provision_registrar_access(user)
            users[username] = user

        departments = {}
        for code, name in DEPARTMENTS:
            department, _ = Department.objects.get_or_create(
                code=code,
                defaults={"name": name, "is_generated": True},
            )
            if department.name != name:
                raise CommandError(
                    f"Department code {code!r} already belongs to {department.name!r}."
                )
            departments[code] = department

        instructor_departments = {
            "demo_instructor1": departments["CST"],
            "demo_instructor2": departments["BUS"],
        }
        for faculty_id, username in (
            ("FAC-0001", "demo_instructor1"),
            ("FAC-0002", "demo_instructor2"),
        ):
            profile = FacultyProfile.objects.filter(user=users[username]).first()
            if profile is None:
                if FacultyProfile.objects.filter(faculty_id=faculty_id).exists():
                    raise CommandError(
                        f"Faculty ID {faculty_id!r} already belongs to another account."
                    )
                FacultyProfile.objects.create(
                    user=users[username],
                    faculty_id=faculty_id,
                    department=instructor_departments[username],
                    specialization="General Studies",
                    is_generated=True,
                )

        academic_year = AcademicYear.objects.filter(is_current=True).first()
        if academic_year is None:
            today = timezone.localdate()
            start_year = today.year if today.month >= 6 else today.year - 1
            start_date = date(start_year, 6, 1)
            end_date = date(start_year + 1, 5, 31)
            name = f"{start_year}-{start_year + 1}"
            academic_year, _ = AcademicYear.objects.get_or_create(
                name=name,
                defaults={
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_current": True,
                    "is_generated": True,
                },
            )
            if not academic_year.is_current:
                academic_year.is_current = True
                academic_year.save(update_fields=["is_current"])

        term_dates = {
            Semester.Term.FIRST: (
                academic_year.start_date,
                min(academic_year.end_date, date(academic_year.start_date.year, 12, 31)),
            ),
            Semester.Term.SECOND: (
                max(
                    academic_year.start_date,
                    date(academic_year.end_date.year, 1, 1),
                ),
                academic_year.end_date,
            ),
        }
        semesters = {}
        for term, (start_date, end_date) in term_dates.items():
            if start_date <= end_date:
                semester, _ = Semester.objects.get_or_create(
                    academic_year=academic_year,
                    term=term,
                    defaults={
                        "start_date": start_date,
                        "end_date": end_date,
                        "is_generated": True,
                    },
                )
                semesters[term] = semester

        courses = {}
        for code, name in COURSES:
            course = Course.objects.filter(code=code).first()
            if course is None:
                course = Course.objects.filter(name=name).first()
            if course is None:
                course = Course.objects.create(
                    code=code,
                    name=name,
                    department=departments[COURSE_DEPARTMENTS[code]],
                    is_generated=True,
                )
            elif course.name != name and course.code == code:
                raise CommandError(
                    f"Course code {code!r} already belongs to {course.name!r}."
                )
            elif not course.is_generated:
                raise CommandError(
                    f"Course {code!r} already exists as a non-generated record. "
                    "Review it manually before provisioning starter data."
                )
            courses[code] = course

        curricula = {}
        sections = {}
        for code, course in courses.items():
            curriculum, _ = Curriculum.objects.get_or_create(
                course=course,
                name="Institutional Curriculum",
                defaults={
                    "effective_from": academic_year.start_date,
                    "is_generated": True,
                },
            )
            curricula[code] = curriculum
            for term, semester in semesters.items():
                section_name = "YEAR1-A" if term == Semester.Term.FIRST else "YEAR1-B"
                section, _ = ClassSection.objects.get_or_create(
                    course=course,
                    semester=semester,
                    name=section_name,
                    defaults={"year_level": 1, "is_generated": True},
                )
                sections[(code, term)] = section

        subject_records = {}
        for code, name, course_code, instructor_username in SUBJECTS:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "course": courses[course_code],
                    "is_generated": True,
                },
            )
            if subject.name != name or subject.course_id != courses[course_code].pk:
                raise CommandError(
                    f"Subject code {code!r} already belongs to another subject."
                )
            if not created and not subject.is_generated:
                raise CommandError(
                    f"Subject {code!r} already exists as a non-generated record. "
                    "Review it manually before provisioning starter data."
                )
            subject.instructors.add(users[instructor_username])
            subject_records[code] = subject

        for course_code, prefix, names in COURSE_SUBJECTS:
            curriculum = curricula[course_code]
            for index, _ in enumerate(names, start=1):
                subject_code = f"{prefix}{index:02d}"
                term = (
                    Semester.Term.FIRST
                    if index <= 5
                    else Semester.Term.SECOND
                )
                semester = semesters.get(term)
                if semester is None:
                    continue
                subject = subject_records[subject_code]
                CurriculumSubject.objects.get_or_create(
                    curriculum=curriculum,
                    subject=subject,
                    defaults={
                        "semester": semester,
                        "year_level": 1,
                        "units": subject.units,
                        "is_generated": True,
                    },
                )
                instructor_username = next(
                    entry[3] for entry in SUBJECTS if entry[0] == subject_code
                )
                class_subject, _ = SectionSubject.objects.get_or_create(
                    section=sections[(course_code, term)],
                    subject=subject,
                    defaults={
                        "instructor": FacultyProfile.objects.get(
                            user=users[instructor_username]
                        ),
                        "is_generated": True,
                    },
                )
                schedule_day = (
                    ClassSchedule.Day.TUESDAY
                    if index % 2
                    else ClassSchedule.Day.THURSDAY
                )
                start_hour = 8 + (index - 1) // 2
                ClassSchedule.objects.get_or_create(
                    class_subject=class_subject,
                    day=schedule_day,
                    defaults={
                        "start_time": f"{start_hour:02d}:00",
                        "end_time": f"{start_hour + 1:02d}:00",
                        "room": f"{course_code}-{index:02d}",
                        "is_generated": True,
                    },
                )

        generated_students = []
        for index, (student_id, username, course_code) in enumerate(STUDENTS, start=1):
            user = users[username]
            student, created = Student.objects.get_or_create(
                student_id=student_id,
                defaults={
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email,
                    "date_of_birth": f"{2004 + index % 3:04d}-{1 + index % 12:02d}-15",
                    "course": courses[course_code],
                    "enrollment_date": "2025-09-01",
                    "user": user,
                    "is_generated": True,
                },
            )
            if not created and not student.is_generated:
                raise CommandError(
                    f"Student ID {student_id!r} already belongs to a non-generated record. "
                    "Review it manually before provisioning starter data."
                )
            if student.user_id not in (None, user.pk):
                raise CommandError(
                    f"Student ID {student_id!r} is already linked to another account."
                )
            if student.user_id is None:
                student.user = user
                student.save(update_fields=["user"])
            generated_students.append(student)
            UserProfile.objects.get_or_create(
                user=user, defaults={"role": UserProfile.Role.STUDENT}
            )
            if not semesters:
                continue
            term = Semester.Term.FIRST
            semester = semesters[term]
            section = sections[(course_code, term)]
            enrollment, _ = Enrollment.objects.get_or_create(
                student=student,
                semester=semester,
                defaults={
                    "section": section,
                    "status": Enrollment.Status.APPROVED,
                    "is_generated": True,
                },
            )
            for class_subject in section.class_subjects.all():
                enrollment_subject, _ = EnrollmentSubject.objects.get_or_create(
                    enrollment=enrollment,
                    class_subject=class_subject,
                    defaults={"is_generated": True},
                )
                subject_index = int(class_subject.subject.code[-2:])
                grade, _ = Grade.objects.get_or_create(
                    enrollment_subject=enrollment_subject,
                    defaults={
                        "midterm_grade": 78 + (index + subject_index) % 17,
                        "final_grade": 80 + (index * 2 + subject_index) % 17,
                        "remarks": "Generated record; verify before official use.",
                        "is_generated": True,
                    },
                )
                today = timezone.localdate()
                target_weekday = 1 if subject_index % 2 else 3
                days_since_class = (today.weekday() - target_weekday) % 7
                latest_class = today - timedelta(days=days_since_class or 7)
                for week in range(6):
                    class_date = latest_class - timedelta(weeks=week)
                    status = (
                        AttendanceRecord.Status.ABSENT
                        if (index + subject_index + week) % 9 == 0
                        else AttendanceRecord.Status.PRESENT
                    )
                    AttendanceRecord.objects.get_or_create(
                        enrollment_subject=enrollment_subject,
                        class_date=class_date,
                        defaults={
                            "status": status,
                            "marked_by": users["demo_instructor1"],
                            "is_generated": True,
                        },
                    )

        for index, (application_number, first_name, last_name, email, course_code, status) in enumerate(
            (
                (
                    "ADM-DEMO-001",
                    "Sample Applicant One",
                    "Example",
                    "applicant1@example.test",
                    "BSCS",
                    AdmissionApplication.Status.SUBMITTED,
                ),
                (
                    "ADM-DEMO-002",
                    "Sample Applicant Two",
                    "Example",
                    "applicant2@example.test",
                    "BSIT",
                    AdmissionApplication.Status.UNDER_REVIEW,
                ),
            ),
            start=1,
        ):
            application, created = AdmissionApplication.objects.get_or_create(
                application_number=application_number,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone": "000-000-0000",
                    "date_of_birth": date(2005, 1, index),
                    "address": "Generated sample data only; not a real applicant.",
                    "preferred_course": courses[course_code],
                    "status": status,
                    "review_notes": (
                        "Generated example; review before using this workflow."
                        if status == AdmissionApplication.Status.UNDER_REVIEW
                        else ""
                    ),
                    "reviewed_by": (
                        users["demo_registrar"]
                        if status == AdmissionApplication.Status.UNDER_REVIEW
                        else None
                    ),
                    "reviewed_at": (
                        timezone.now()
                        if status == AdmissionApplication.Status.UNDER_REVIEW
                        else None
                    ),
                    "is_generated": True,
                },
            )
            if not created and not application.is_generated:
                raise CommandError(
                    f"Application number {application_number!r} belongs to a "
                    "non-generated record."
                )
            requirement_name = "Sample supporting document"
            admission_document = AdmissionDocument.objects.filter(
                application=application,
                requirement_name=requirement_name,
            ).first()
            if admission_document and not admission_document.is_generated:
                raise CommandError(
                    f"The {requirement_name!r} for {application_number!r} is "
                    "a non-generated record."
                )
            if admission_document is None:
                document = AdmissionDocument(
                    application=application,
                    requirement_name=requirement_name,
                    status=AdmissionDocument.Status.RECEIVED,
                    notes="Generated sample PDF; not a real identity document.",
                    is_generated=True,
                )
                document.file.save(
                    f"sample-admission-{index}.pdf",
                    ContentFile(build_sample_pdf()),
                    save=False,
                )
                document.save()

        for index, student in enumerate(generated_students, start=1):
            document_number = f"DOC-DEMO-{index:04d}"
            issued = index <= 5
            document, created = StudentDocument.objects.get_or_create(
                document_number=document_number,
                defaults={
                    "student": student,
                    "document_type": (
                        StudentDocument.Type.ENROLLMENT
                        if issued
                        else StudentDocument.Type.TRANSCRIPT
                    ),
                    "status": (
                        StudentDocument.Status.ISSUED
                        if issued
                        else StudentDocument.Status.REQUESTED
                    ),
                    "issued_at": timezone.now() if issued else None,
                    "issued_by": users["demo_registrar"] if issued else None,
                    "notes": "Generated example; not an official student document.",
                    "is_generated": True,
                },
            )
            if not created and not document.is_generated:
                raise CommandError(
                    f"Document number {document_number!r} belongs to a "
                    "non-generated record."
                )

        for action, entity_type, entity_id, description in (
            (
                AuditLog.Action.CREATE,
                "admissions.AdmissionApplication",
                "ADM-DEMO-001",
                "Generated sample activity: a demonstration admission application was submitted.",
            ),
            (
                AuditLog.Action.CREATE,
                "documents.StudentDocument",
                "DOC-DEMO-0001",
                "Generated sample activity: a demonstration enrollment document was issued.",
            ),
        ):
            activity = AuditLog.objects.filter(
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
            ).first()
            if activity and not activity.is_generated:
                raise CommandError(
                    f"Sample activity {entity_type} {entity_id} conflicts with "
                    "a non-generated audit record."
                )
            if activity is None:
                AuditLog.objects.create(
                    actor=users["demo_registrar"],
                    action=action,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    description=description,
                    is_generated=True,
                )

        self.stdout.write(self.style.SUCCESS("Institutional starter records are ready."))
        self.stdout.write("Accounts: 1 registrar, 2 instructors, and 10 students.")
        self.stdout.write("Academic catalog: 10 courses and 100 subjects.")
        self.stdout.write("Workflow examples: admissions, sample documents, and audit history.")
        self.stdout.write("Generated academic records are marked as unverified.")
        if created_credentials:
            self.stdout.write(
                self.style.WARNING(
                    "Save these one-time credentials now; they are not shown again."
                )
            )
            for username, password in created_credentials:
                self.stdout.write(f"{username}: {password}")
        else:
            self.stdout.write("No accounts were created; existing passwords were unchanged.")
