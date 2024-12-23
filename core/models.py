from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission, User
from django.utils import timezone
import string,random
import datetime
from django.contrib.auth.hashers import make_password
from django.db.models import UniqueConstraint

class CustomUser(AbstractUser):
    user_type_choices = (
        (1, "Admin"),
        (2, "CompanyAdmin"),
        (3, "HR"),
        (4, "Manager"),
        (5, "Employee")
    )
    user_type = models.PositiveSmallIntegerField(choices=user_type_choices, default=5)
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True, related_name='users')
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    def __str__(self):
        return self.username

class Company(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField()
    email = models.EmailField()
    contact_info = models.CharField(max_length=255)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    company_code_for_employee_id = models.CharField(max_length=5, unique=True, blank=True, null=True)
    date_of_registration = models.DateField(auto_now_add=True)


    def generate_company_code(self):
        letters_and_digits = string.ascii_uppercase + string.digits
        return ''.join(random.choices(letters_and_digits, k=5))

    def save(self, *args, **kwargs):
        if not self.company_code_for_employee_id:
            self.company_code_for_employee_id = self.generate_company_code()
            while Company.objects.filter(company_code_for_employee_id=self.company_code_for_employee_id).exists():
                self.company_code_for_employee_id = self.generate_company_code()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.users.all().delete()
        self.departments.all().delete()
        self.roles.all().delete()
        self.employees.all().delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="departments")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['name', 'company'], name='unique_department_per_company')
        ]
        ordering = ['name']

    def __str__(self):
        return self.name


class Role(models.Model):
    name = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="roles")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='roles')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Employee(models.Model):
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=15)
    email = models.EmailField(max_length=255, unique=True)
    employee_id = models.CharField(max_length=50, unique=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="employees")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="employees")
    joining_date = models.DateField()
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="employees")
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    image = models.ImageField(upload_to='employee_images/', blank=True, null=True)

    def generate_employee_id(self):
        company_code = self.company.company_code_for_employee_id
        last_employee = Employee.objects.filter(company=self.company).order_by('-employee_id').first()
        if last_employee:
            last_id = int(last_employee.employee_id.split('-')[1])
            new_id = str(last_id + 1).zfill(4)
        else:
            new_id = '0001'
        return f"{company_code}-{new_id}"

    def save(self, *args, **kwargs):
        if not self.employee_id:
            self.employee_id = self.generate_employee_id()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.employee_id})"
    

class Attendance(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE)
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    date = models.DateField()
    status_choices = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
        ('Late', 'Late'),
    ]
    status = models.CharField(max_length=10, choices=status_choices)
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    correction_requested = models.BooleanField(default=False)
    correction_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"{self.employee.name} - {self.status} on {self.date}"

    class Meta:
        unique_together = ('employee', 'date')

# LeaveRequest model

       
class LeavePolicy(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    leave_type =  models.CharField(max_length=255, unique=True)  # Changed from CharField to TextField
    max_days_per_year = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.company.name} - {self.leave_type}"
    
    class Meta:
        unique_together = ("company", "leave_type")
    
    
class LeaveBalance(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeavePolicy, on_delete=models.CASCADE)
    remaining_days = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type.leave_type} - {self.remaining_days} days"
    
    def update_leave_balance(self, days_taken):
        if days_taken > self.remaining_days:
            raise ValidationError("Insufficient leave balance.")
        self.remaining_days -= days_taken
        self.save()
    
    
class LeaveRequest(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeavePolicy, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status_choices = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]
    status = models.CharField(max_length=10, choices=status_choices, default="Pending")
    reason = models.TextField()
    manager_comments = models.TextField(blank=True, null=True)
    request_date = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.employee.name} - {self.leave_type.leave_type} - {self.status}"

    def clean(self):
        # Ensure end_date is not before start_date
        if self.start_date > self.end_date:
            raise ValidationError("End date cannot be before start date.")

    def approve_leave(self):
        if self.status != "Pending":
            raise ValidationError("Leave request is not in a Pending state.")
        
        days_taken = (self.end_date - self.start_date).days + 1  # Include start and end date
        leave_balance = LeaveBalance.objects.get(employee=self.employee, leave_type=self.leave_type)

        if leave_balance.remaining_days >= days_taken:
            leave_balance.update_leave_balance(days_taken)
            self.status = "Approved"
            self.save()
        else:
            raise ValidationError("Insufficient leave balance.")
    
    
class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    task_name = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='tasks')
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    company = models.ForeignKey('Company', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.task_name} - {self.status}"

    class Meta:
        ordering = ['-deadline']
        
class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']