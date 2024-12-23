from django.contrib import admin
from .models import Company, Department, Role, Employee, Attendance, LeaveRequest,Attendance,LeavePolicy,LeaveBalance,CustomUser,Task,Announcement


admin.site.register(CustomUser)
admin.site.register(Company)
admin.site.register(Department)
class DepartmetAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')

admin.site.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'company')
    
admin.site.register(Employee)

admin.site.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'status')
    list_filter = ('date', 'status')

admin.site.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status')
    list_filter = ('status', 'leave_type', 'start_date')

admin.site.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = ('company', 'leave_type', 'max_days_per_year')

admin.site.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'remaining_days')
    
admin.site.register(Task)
admin.site.register(Announcement)
