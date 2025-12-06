"""
Database Seeder Command
ایجاد داده‌های اولیه برای سایت کانون
python manage.py seed_database
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import random
from datetime import timedelta, date, time
import uuid


class Command(BaseCommand):
    help = 'Seed database with initial data for the Kanoon LMS'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before seeding',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('🌱 Starting database seeding...'))
        
        try:
            with transaction.atomic():
                if options['clear']:
                    self.clear_data()
                
                self.seed_grade_levels()
                self.seed_users()
                self.seed_branches()
                self.seed_subjects()
                self.seed_courses()
                self.seed_terms()
                self.seed_classes()
                self.seed_enrollments()
                self.seed_invoices()
                self.seed_coupons()
                self.seed_notifications()
                self.seed_crm_data()
                
            self.stdout.write(self.style.SUCCESS('✅ Database seeding completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            raise e

    def clear_data(self):
        """Clear existing data (optional)"""
        self.stdout.write('  🗑️  Clearing existing data...')
        from apps.enrollments.models import Enrollment
        from apps.financial.models import Invoice, Payment, DiscountCoupon
        from apps.courses.models import Class, Course, Subject, Term, ClassSession
        from apps.branches.models import Branch, Classroom
        from apps.notifications.models import Notification, Announcement
        from apps.crm.models import Lead, LeadActivity
        
        # Don't delete users - just the data
        Enrollment.objects.all().delete()
        Invoice.objects.all().delete()
        Payment.objects.all().delete()
        ClassSession.objects.all().delete()
        Class.objects.all().delete()
        Course.objects.all().delete()
        Subject.objects.all().delete()
        Term.objects.all().delete()
        Classroom.objects.all().delete()
        Branch.objects.all().delete()
        Notification.objects.all().delete()
        Announcement.objects.all().delete()
        Lead.objects.all().delete()
        DiscountCoupon.objects.all().delete()

    def seed_grade_levels(self):
        """Create grade levels"""
        self.stdout.write('  📚 Creating grade levels...')
        from apps.accounts.models import GradeLevel
        
        grades = [
            ('هفتم', 7, 'middle_school'),
            ('هشتم', 8, 'middle_school'),
            ('نهم', 9, 'middle_school'),
            ('دهم ریاضی', 10, 'high_school'),
            ('دهم تجربی', 11, 'high_school'),
            ('دهم انسانی', 12, 'high_school'),
            ('یازدهم ریاضی', 13, 'high_school'),
            ('یازدهم تجربی', 14, 'high_school'),
            ('یازدهم انسانی', 15, 'high_school'),
            ('دوازدهم ریاضی', 16, 'high_school'),
            ('دوازدهم تجربی', 17, 'high_school'),
            ('دوازدهم انسانی', 18, 'high_school'),
            ('کنکور ریاضی', 19, 'other'),
            ('کنکور تجربی', 20, 'other'),
            ('کنکور انسانی', 21, 'other'),
        ]
        
        self.grade_levels = {}
        for name, order, stage in grades:
            obj, created = GradeLevel.objects.get_or_create(
                name=name,
                defaults={
                    'order': order,
                    'stage': stage,
                    'is_active': True,
                }
            )
            self.grade_levels[name] = obj
        
        self.stdout.write(f'    ✓ Created {len(grades)} grade levels')

    def seed_users(self):
        """Create users for different roles"""
        self.stdout.write('  👥 Creating users...')
        from apps.accounts.models import User, StudentProfile, TeacherProfile
        
        # Super Admin
        self.admin, created = User.objects.get_or_create(
            national_code='0000000001',
            defaults={
                'first_name': 'مدیر',
                'last_name': 'سیستم',
                'mobile': '09120000001',
                'email': 'admin@kanoon.ir',
                'role': User.UserRole.SUPER_ADMIN,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        
        # Branch Managers
        self.branch_managers = []
        manager_data = [
            ('علی', 'احمدی', '0000000010', '09120000010'),
            ('محمد', 'رضایی', '0000000011', '09120000011'),
            ('حسین', 'محمدی', '0000000012', '09120000012'),
        ]
        for first, last, nc, mobile in manager_data:
            user, created = User.objects.get_or_create(
                national_code=nc,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'mobile': mobile,
                    'role': User.UserRole.BRANCH_MANAGER,
                }
            )
            self.branch_managers.append(user)
        
        # Teachers
        self.teachers = []
        teacher_data = [
            ('استاد', 'کریمی', '0000000020', '09120000020', 'ریاضی'),
            ('استاد', 'حسینی', '0000000021', '09120000021', 'فیزیک'),
            ('استاد', 'موسوی', '0000000022', '09120000022', 'شیمی'),
            ('استاد', 'هاشمی', '0000000023', '09120000023', 'زیست'),
            ('استاد', 'نوری', '0000000024', '09120000024', 'ادبیات'),
            ('استاد', 'صادقی', '0000000025', '09120000025', 'عربی'),
            ('استاد', 'باقری', '0000000026', '09120000026', 'زبان انگلیسی'),
            ('استاد', 'رحیمی', '0000000027', '09120000027', 'دین و زندگی'),
        ]
        for first, last, nc, mobile, subject in teacher_data:
            user, created = User.objects.get_or_create(
                national_code=nc,
                defaults={
                    'first_name': first,
                    'last_name': last,
                    'mobile': mobile,
                    'role': User.UserRole.TEACHER,
                }
            )
            if created:
                TeacherProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'expertise': subject,
                        'bio': f'استاد با تجربه درس {subject}',
                        'education_degree': 'کارشناسی ارشد',
                        'hourly_rate': random.randint(200000, 500000),
                        'experience_years': random.randint(3, 15),
                        'status': 'active',
                    }
                )
            self.teachers.append(user)
        
        # Students
        self.students = []
        first_names = ['محمد', 'علی', 'حسین', 'مهدی', 'امیر', 'رضا', 'سعید', 'فاطمه', 'زهرا', 'مریم', 'سارا', 'نرگس']
        last_names = ['احمدی', 'رضایی', 'محمدی', 'کریمی', 'حسینی', 'موسوی', 'هاشمی', 'نوری', 'صادقی']
        
        for i in range(30):
            nc = f'000000{100 + i:04d}'
            mobile = f'0912000{100 + i:04d}'
            user, created = User.objects.get_or_create(
                national_code=nc,
                defaults={
                    'first_name': random.choice(first_names),
                    'last_name': random.choice(last_names),
                    'mobile': mobile,
                    'role': User.UserRole.STUDENT,
                }
            )
            if created:
                grade = random.choice(list(self.grade_levels.values())) if self.grade_levels else None
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'grade_level': grade,
                        'school_name': f'دبیرستان شماره {random.randint(1, 20)}',
                        'guardian_name': f'{random.choice(first_names)} {random.choice(last_names)}',
                        'guardian_mobile': f'0912{random.randint(1000000, 9999999)}',
                        'education_level': 'high_school',
                        'is_active_student': True,
                    }
                )
            self.students.append(user)
        
        # Accountant
        self.accountant, _ = User.objects.get_or_create(
            national_code='0000000030',
            defaults={
                'first_name': 'حسابدار',
                'last_name': 'سیستم',
                'mobile': '09120000030',
                'role': User.UserRole.ACCOUNTANT,
            }
        )
        
        # Receptionist
        self.receptionist, _ = User.objects.get_or_create(
            national_code='0000000031',
            defaults={
                'first_name': 'پذیرش',
                'last_name': 'سیستم',
                'mobile': '09120000031',
                'role': User.UserRole.RECEPTIONIST,
            }
        )
        
        self.stdout.write(f'    ✓ Created users (1 admin, {len(self.branch_managers)} managers, {len(self.teachers)} teachers, {len(self.students)} students)')

    def seed_branches(self):
        """Create branches and classrooms"""
        self.stdout.write('  🏢 Creating branches...')
        from apps.branches.models import Branch, Classroom
        
        branches_data = [
            ('شعبه مرکزی تهران', 'تهران', 'تهران', 'میدان ولیعصر، خیابان کریمخان', '02188001234', 150),
            ('شعبه شمال تهران', 'تهران', 'تهران', 'میدان تجریش، خیابان شریعتی', '02122001234', 100),
            ('شعبه اصفهان', 'اصفهان', 'اصفهان', 'خیابان چهارباغ عباسی', '03132001234', 80),
            ('شعبه شیراز', 'فارس', 'شیراز', 'خیابان زند، نبش کوچه ۱۵', '07136001234', 70),
            ('شعبه مشهد', 'خراسان رضوی', 'مشهد', 'بلوار سجاد، خیابان بهار', '05138001234', 90),
        ]
        
        self.branches = []
        for i, (name, province, city, address, phone, capacity) in enumerate(branches_data):
            code = f'BR{str(i+1).zfill(3)}'
            branch, created = Branch.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'province': province,
                    'city': city,
                    'address': address,
                    'phone': phone,
                    'total_capacity': capacity,
                    'status': 'active',
                    'manager': self.branch_managers[i % len(self.branch_managers)],
                    'working_hours_start': time(8, 0),
                    'working_hours_end': time(20, 0),
                    'working_days': 'شنبه تا پنجشنبه',
                    'established_date': date(2020, 1, 1) + timedelta(days=random.randint(0, 1000)),
                }
            )
            self.branches.append(branch)
            
            # Create classrooms for each branch
            if created:
                for j in range(1, random.randint(5, 10)):
                    Classroom.objects.create(
                        branch=branch,
                        name=f'کلاس {j}',
                        room_number=f'{j:02d}',
                        capacity=random.choice([15, 20, 25, 30]),
                        has_projector=random.choice([True, False]),
                        has_whiteboard=True,
                        is_active=True,
                    )
        
        self.stdout.write(f'    ✓ Created {len(branches_data)} branches with classrooms')

    def seed_subjects(self):
        """Create subjects (lessons)"""
        self.stdout.write('  📖 Creating subjects...')
        from apps.courses.models import Subject
        
        subjects_data = [
            ('ریاضی ۱', 'MATH1', 400000, 24),
            ('ریاضی ۲', 'MATH2', 450000, 24),
            ('ریاضی ۳', 'MATH3', 500000, 24),
            ('فیزیک ۱', 'PHY1', 400000, 24),
            ('فیزیک ۲', 'PHY2', 450000, 24),
            ('فیزیک ۳', 'PHY3', 500000, 24),
            ('شیمی ۱', 'CHEM1', 400000, 24),
            ('شیمی ۲', 'CHEM2', 450000, 24),
            ('شیمی ۳', 'CHEM3', 500000, 24),
            ('زیست‌شناسی ۱', 'BIO1', 400000, 24),
            ('زیست‌شناسی ۲', 'BIO2', 450000, 24),
            ('زیست‌شناسی ۳', 'BIO3', 500000, 24),
            ('ادبیات فارسی', 'LIT', 350000, 20),
            ('عربی عمومی', 'ARB1', 300000, 20),
            ('عربی اختصاصی', 'ARB2', 350000, 20),
            ('زبان انگلیسی', 'ENG', 400000, 24),
            ('دین و زندگی', 'REL', 300000, 16),
            ('زمین‌شناسی', 'GEO', 300000, 16),
            ('هندسه', 'GEOM', 400000, 20),
            ('حسابان', 'CALC', 450000, 24),
            ('آمار و مدلسازی', 'STAT', 300000, 16),
            ('گسسته', 'DISC', 350000, 20),
        ]
        
        self.subjects = []
        grade_list = list(self.grade_levels.values())
        for title, code, price, sessions in subjects_data:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'title': title,
                    'base_price': price,
                    'standard_sessions': sessions,
                    'grade_level': random.choice(grade_list) if grade_list else None,
                    'is_active': True,
                }
            )
            self.subjects.append(subject)
        
        self.stdout.write(f'    ✓ Created {len(subjects_data)} subjects')

    def seed_courses(self):
        """Create courses"""
        self.stdout.write('  📚 Creating courses...')
        from apps.courses.models import Course
        
        courses_data = [
            ('دوره جامع ریاضی کنکور', 'riazi-jame-konkour', 'دوره کامل ریاضیات برای کنکور', 'advanced', 120, 60, 8000000),
            ('دوره جامع فیزیک کنکور', 'fizik-jame-konkour', 'دوره کامل فیزیک برای کنکور', 'advanced', 100, 50, 7500000),
            ('دوره جامع شیمی کنکور', 'shimi-jame-konkour', 'دوره کامل شیمی برای کنکور', 'advanced', 90, 45, 7000000),
            ('دوره جامع زیست کنکور', 'zist-jame-konkour', 'دوره کامل زیست‌شناسی برای کنکور', 'advanced', 100, 50, 7500000),
            ('ریاضی پایه دهم', 'riazi-dahom', 'آموزش ریاضی پایه دهم', 'intermediate', 60, 30, 4000000),
            ('فیزیک پایه دهم', 'fizik-dahom', 'آموزش فیزیک پایه دهم', 'intermediate', 50, 25, 3500000),
            ('شیمی پایه دهم', 'shimi-dahom', 'آموزش شیمی پایه دهم', 'intermediate', 50, 25, 3500000),
            ('ریاضی پایه یازدهم', 'riazi-yazdahom', 'آموزش ریاضی پایه یازدهم', 'intermediate', 60, 30, 4500000),
            ('فیزیک پایه یازدهم', 'fizik-yazdahom', 'آموزش فیزیک پایه یازدهم', 'intermediate', 50, 25, 4000000),
            ('زبان انگلیسی جامع', 'zaban-jame', 'دوره جامع زبان انگلیسی', 'beginner', 80, 40, 5000000),
            ('عربی کنکور', 'arabi-konkour', 'آموزش کامل عربی برای کنکور', 'intermediate', 40, 20, 3000000),
            ('ادبیات و زبان فارسی', 'adabiat-farsi', 'دوره جامع ادبیات فارسی', 'intermediate', 50, 25, 3500000),
        ]
        
        self.courses = []
        for name, slug, desc, level, hours, sessions, price in courses_data:
            code = f"CRS{len(self.courses)+1:03d}"
            course, created = Course.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'code': code,
                    'description': f'{desc}\n\nاین دوره شامل:\n- جزوات کامل\n- آزمون‌های دوره‌ای\n- پشتیبانی آنلاین',
                    'short_description': desc,
                    'level': level,
                    'duration_hours': hours,
                    'sessions_count': sessions,
                    'base_price': price,
                    'status': 'active',
                    'syllabus': '- فصل اول: مقدمات\n- فصل دوم: مباحث اصلی\n- فصل سوم: تمرین و تست\n- فصل چهارم: جمع‌بندی',
                    'learning_outcomes': '- تسلط بر مباحث اصلی\n- توانایی حل تست\n- آمادگی برای آزمون',
                    'min_students': 5,
                    'max_students': 30,
                    'is_featured': random.choice([True, False]),
                    'provides_certificate': True,
                }
            )
            if created and self.subjects:
                # Add random subjects to course
                course.subjects.set(random.sample(self.subjects, min(3, len(self.subjects))))
            self.courses.append(course)
        
        self.stdout.write(f'    ✓ Created {len(courses_data)} courses')

    def seed_terms(self):
        """Create academic terms"""
        self.stdout.write('  📅 Creating terms...')
        from apps.courses.models import Term
        
        today = timezone.now().date()
        
        terms_data = [
            ('ترم پاییز ۱۴۰۳', 'FALL1403', today - timedelta(days=60), today + timedelta(days=30)),
            ('ترم زمستان ۱۴۰۳', 'WIN1403', today + timedelta(days=31), today + timedelta(days=120)),
            ('ترم بهار ۱۴۰۴', 'SPR1404', today + timedelta(days=121), today + timedelta(days=210)),
        ]
        
        self.terms = []
        for name, code, start, end in terms_data:
            status = 'active' if start <= today <= end else ('upcoming' if start > today else 'completed')
            term, created = Term.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'start_date': start,
                    'end_date': end,
                    'registration_start': start - timedelta(days=30),
                    'registration_end': start + timedelta(days=7),
                    'status': status,
                    'early_registration_discount': Decimal('10.00'),
                    'early_registration_deadline': start - timedelta(days=15),
                }
            )
            self.terms.append(term)
        
        self.stdout.write(f'    ✓ Created {len(terms_data)} terms')

    def seed_classes(self):
        """Create classes"""
        self.stdout.write('  🎓 Creating classes...')
        from apps.courses.models import Class
        from apps.branches.models import Classroom
        
        self.classes = []
        today = timezone.now().date()
        
        for i, course in enumerate(self.courses[:8]):  # Create classes for first 8 courses
            for j, branch in enumerate(self.branches[:3]):  # In first 3 branches
                classroom = Classroom.objects.filter(branch=branch).first()
                teacher = self.teachers[i % len(self.teachers)]
                
                code = f"CLS{len(self.classes)+1:04d}"
                start_date = today + timedelta(days=random.randint(7, 30))
                end_date = start_date + timedelta(days=90)
                
                class_obj, created = Class.objects.get_or_create(
                    code=code,
                    defaults={
                        'course': course,
                        'branch': branch,
                        'classroom': classroom,
                        'teacher': teacher,
                        'name': f'{course.name} - گروه {j+1}',
                        'class_type': random.choice(['in_person', 'online', 'hybrid']),
                        'start_date': start_date,
                        'end_date': end_date,
                        'schedule_days': ['saturday', 'monday', 'wednesday'],
                        'start_time': time(random.choice([8, 10, 14, 16]), 0),
                        'end_time': time(random.choice([10, 12, 16, 18]), 0),
                        'capacity': random.choice([15, 20, 25]),
                        'current_enrollments': 0,
                        'price': course.base_price,
                        'registration_start': timezone.now(),
                        'registration_end': timezone.now() + timedelta(days=30),
                        'is_registration_open': True,
                        'status': 'scheduled',
                    }
                )
                self.classes.append(class_obj)
        
        self.stdout.write(f'    ✓ Created {len(self.classes)} classes')

    def seed_enrollments(self):
        """Create enrollments"""
        self.stdout.write('  📝 Creating enrollments...')
        from apps.enrollments.models import Enrollment
        
        for student in self.students[:20]:  # Enroll first 20 students
            # Each student enrolls in 1-3 classes
            num_classes = random.randint(1, 3)
            student_classes = random.sample(self.classes, min(num_classes, len(self.classes)))
            
            for class_obj in student_classes:
                enrollment, created = Enrollment.objects.get_or_create(
                    student=student,
                    class_obj=class_obj,
                    defaults={
                        'status': random.choice(['active', 'active', 'active', 'pending']),
                        'total_amount': class_obj.price,
                        'discount_amount': random.choice([0, 0, 500000, 1000000]),
                        'final_amount': class_obj.price - random.choice([0, 0, 500000, 1000000]),
                        'paid_amount': class_obj.price if random.random() > 0.3 else 0,
                    }
                )
                if created:
                    class_obj.current_enrollments += 1
                    class_obj.save()
        
        self.stdout.write('    ✓ Created enrollments')

    def seed_invoices(self):
        """Create invoices"""
        self.stdout.write('  🧾 Creating invoices...')
        from apps.financial.models import Invoice, InvoiceItem
        from apps.enrollments.models import Enrollment
        
        enrollments = Enrollment.objects.all()[:15]
        
        for enrollment in enrollments:
            invoice, created = Invoice.objects.get_or_create(
                student=enrollment.student,
                enrollment=enrollment,
                defaults={
                    'branch': enrollment.class_obj.branch,
                    'invoice_type': 'tuition',
                    'subtotal': enrollment.total_amount,
                    'discount_amount': enrollment.discount_amount,
                    'tax_amount': 0,
                    'total_amount': enrollment.final_amount,
                    'paid_amount': enrollment.paid_amount,
                    'issue_date': timezone.now().date() - timedelta(days=random.randint(0, 30)),
                    'due_date': timezone.now().date() + timedelta(days=random.randint(7, 30)),
                    'description': f'شهریه کلاس {enrollment.class_obj.name}',
                    'created_by': self.admin,
                }
            )
            
            if created:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    description=f'شهریه {enrollment.class_obj.name}',
                    quantity=1,
                    unit_price=enrollment.total_amount,
                )
        
        self.stdout.write('    ✓ Created invoices')

    def seed_coupons(self):
        """Create discount coupons"""
        self.stdout.write('  🎫 Creating coupons...')
        from apps.financial.models import DiscountCoupon
        
        today = timezone.now().date()
        
        coupons_data = [
            ('WELCOME2024', 'کوپن خوش‌آمدگویی', 'percentage', 10, 100),
            ('SUMMER50', 'تخفیف تابستانی', 'percentage', 15, 50),
            ('LOYALTY100', 'تخفیف وفاداری', 'fixed', 1000000, 30),
            ('NEWSTUDENT', 'تخفیف دانش‌آموز جدید', 'percentage', 20, 200),
            ('VIP25', 'تخفیف ویژه', 'percentage', 25, 20),
        ]
        
        for code, name, dtype, value, max_uses in coupons_data:
            DiscountCoupon.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'discount_type': dtype,
                    'discount_value': value,
                    'valid_from': today - timedelta(days=30),
                    'valid_until': today + timedelta(days=90),
                    'max_uses': max_uses,
                    'current_uses': random.randint(0, max_uses // 2),
                    'is_active': True,
                }
            )
        
        self.stdout.write(f'    ✓ Created {len(coupons_data)} coupons')

    def seed_notifications(self):
        """Create notifications and announcements"""
        self.stdout.write('  🔔 Creating notifications...')
        from apps.notifications.models import Notification, Announcement
        
        # Announcements
        announcements = [
            ('شروع ثبت‌نام ترم زمستان', 'ثبت‌نام ترم زمستان ۱۴۰۳ از امروز آغاز شد. برای استفاده از تخفیف ثبت‌نام زودهنگام عجله کنید!'),
            ('تغییر ساعت کاری', 'ساعت کاری شعب از ۸ صبح تا ۸ شب تغییر یافت.'),
            ('آزمون آزمایشی رایگان', 'آزمون آزمایشی رایگان کنکور در تاریخ ۱۵ آذر برگزار می‌شود.'),
        ]
        
        for title, content in announcements:
            Announcement.objects.get_or_create(
                title=title,
                defaults={
                    'content': content,
                    'is_published': True,
                    'publish_date': timezone.now() - timedelta(days=random.randint(0, 7)),
                    'created_by': self.admin,
                }
            )
        
        # Notifications for students
        for student in self.students[:10]:
            Notification.objects.create(
                recipient=student,
                title='به کانون خوش آمدید!',
                message='ثبت‌نام شما با موفقیت انجام شد. برای مشاهده کلاس‌ها به پنل کاربری مراجعه کنید.',
                notification_type='success',
                category='enrollment',
            )
        
        self.stdout.write('    ✓ Created notifications and announcements')

    def seed_crm_data(self):
        """Create CRM leads and activities"""
        self.stdout.write('  📊 Creating CRM data...')
        from apps.crm.models import Lead, LeadActivity
        
        lead_sources = ['website', 'social_media', 'referral', 'phone', 'walk_in']
        lead_statuses = ['new', 'contacted', 'qualified', 'converted']
        
        first_names = ['امیر', 'رضا', 'حسین', 'مهدی', 'سارا', 'مریم', 'فاطمه']
        last_names = ['نیکزاد', 'قاسمی', 'جعفری', 'یزدانی', 'کاظمی']
        
        for i in range(20):
            mobile = f'091{random.randint(10000000, 99999999)}'
            lead, created = Lead.objects.get_or_create(
                mobile=mobile,
                defaults={
                    'first_name': random.choice(first_names),
                    'last_name': random.choice(last_names),
                    'email': f'lead{i}@example.com',
                    'source': random.choice(lead_sources),
                    'status': random.choice(lead_statuses),
                    'preferred_branch': random.choice(self.branches) if self.branches else None,
                    'interested_course': random.choice(self.courses) if self.courses else None,
                    'score': random.randint(30, 90),
                    'notes': 'سرنخ ایجاد شده توسط seeder',
                    'assigned_to': random.choice(self.branch_managers) if self.branch_managers else None,
                }
            )
            
            if created:
                # Add activities
                for j in range(random.randint(1, 3)):
                    LeadActivity.objects.create(
                        lead=lead,
                        activity_type=random.choice(['call', 'email', 'meeting', 'note']),
                        subject='پیگیری سرنخ',
                        description='پیگیری انجام شد',
                        performed_by=self.admin,
                    )
        
        self.stdout.write('    ✓ Created CRM data')

