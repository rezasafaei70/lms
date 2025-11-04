from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import TimeStampedModel
from apps.accounts.models import User
from apps.courses.models import ClassSession
from apps.enrollments.models import Enrollment


class Attendance(TimeStampedModel):
    """
    Attendance Record Model
    """
    class AttendanceStatus(models.TextChoices):
        PRESENT = 'present', _('حاضر')
        ABSENT = 'absent', _('غایب')
        LATE = 'late', _('تاخیر')
        EXCUSED = 'excused', _('غیبت موجه')
        SICK = 'sick', _('مریضی')

    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('ثبت‌نام')
    )
    
    session = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name=_('جلسه')
    )
    
    # Status
    status = models.CharField(
        _('وضعیت'),
        max_length=10,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.PRESENT
    )
    
    # Time tracking
    check_in_time = models.DateTimeField(_('زمان ورود'), null=True, blank=True)
    check_out_time = models.DateTimeField(_('زمان خروج'), null=True, blank=True)
    
    # Late duration
    late_minutes = models.PositiveIntegerField(_('دقیقه تاخیر'), default=0)
    
    # Recorded by
    recorded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recorded_attendances',
        verbose_name=_('ثبت کننده')
    )
    
    # Notes
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)
    excuse_reason = models.TextField(_('دلیل غیبت'), null=True, blank=True)
    
    # Auto-recorded (for online classes)
    is_auto_recorded = models.BooleanField(_('ثبت خودکار'), default=False)

    class Meta:
        db_table = 'attendances'
        verbose_name = _('حضور و غیاب')
        verbose_name_plural = _('حضور و غیاب')
        ordering = ['-created_at']
        unique_together = ['enrollment', 'session']
        indexes = [
            models.Index(fields=['enrollment', 'status']),
            models.Index(fields=['session']),
        ]

    def __str__(self):
        return f"{self.enrollment.student.get_full_name()} - {self.session}"

    def save(self, *args, **kwargs):
        # Calculate late minutes
        if self.status == self.AttendanceStatus.LATE and self.check_in_time:
            from datetime import datetime, timedelta
            session_start = datetime.combine(
                self.session.date,
                self.session.start_time
            )
            if self.check_in_time.replace(tzinfo=None) > session_start:
                diff = self.check_in_time.replace(tzinfo=None) - session_start
                self.late_minutes = int(diff.total_seconds() / 60)
        
        super().save(*args, **kwargs)
        
        # Update enrollment attendance rate
        self.enrollment.update_attendance_rate()


class AttendanceReport(TimeStampedModel):
    """
    Attendance Report for a class session
    """
    session = models.OneToOneField(
        ClassSession,
        on_delete=models.CASCADE,
        related_name='attendance_report',
        verbose_name=_('جلسه')
    )
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='attendance_reports',
        verbose_name=_('معلم')
    )
    
    # Statistics
    total_students = models.PositiveIntegerField(_('کل دانش‌آموزان'), default=0)
    present_count = models.PositiveIntegerField(_('تعداد حاضر'), default=0)
    absent_count = models.PositiveIntegerField(_('تعداد غایب'), default=0)
    late_count = models.PositiveIntegerField(_('تعداد تاخیر'), default=0)
    excused_count = models.PositiveIntegerField(_('تعداد غیبت موجه'), default=0)
    
    # Percentages
    attendance_rate = models.DecimalField(
        _('نرخ حضور'),
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Submission
    submitted_at = models.DateTimeField(_('زمان ثبت'), auto_now_add=True)
    is_finalized = models.BooleanField(_('نهایی شده'), default=False)
    
    notes = models.TextField(_('یادداشت‌ها'), null=True, blank=True)

    class Meta:
        db_table = 'attendance_reports'
        verbose_name = _('گزارش حضور و غیاب')
        verbose_name_plural = _('گزارشات حضور و غیاب')
        ordering = ['-submitted_at']

    def __str__(self):
        return f"گزارش {self.session}"

    def calculate_statistics(self):
        """Calculate attendance statistics"""
        attendances = self.session.attendances.all()
        
        self.total_students = attendances.count()
        self.present_count = attendances.filter(
            status=Attendance.AttendanceStatus.PRESENT
        ).count()
        self.absent_count = attendances.filter(
            status=Attendance.AttendanceStatus.ABSENT
        ).count()
        self.late_count = attendances.filter(
            status=Attendance.AttendanceStatus.LATE
        ).count()
        self.excused_count = attendances.filter(
            status=Attendance.AttendanceStatus.EXCUSED
        ).count()
        
        if self.total_students > 0:
            self.attendance_rate = (
                (self.present_count + self.late_count) / self.total_students
            ) * 100
        
        self.save()