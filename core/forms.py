from django import forms
from .models import Company, Employee,Department,Role,Announcement,Attendance,LeaveRequest, LeavePolicy
from django.contrib.auth.models import User

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'contact_info','email','logo', 'company_code_for_employee_id']
        
class EmployeeForm(forms.ModelForm):
    # Fields for department and role, initially set to empty querysets
    department = forms.ModelChoiceField(queryset=Department.objects.all(), empty_label="Select Department")
    role = forms.ModelChoiceField(queryset=Role.objects.all(), empty_label="Select Role")
    
    
    
    class Meta:
        model = Employee
        fields = ['name', 'address', 'phone_number', 'role', 'salary', 'status', 'image', 'joining_date', 'department', 'company', 'email']

     
class DepartmentForm(forms.ModelForm):
    class Meta:
        model=Department
        fields=['name','company']
        widgets={
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder':'Enter Department Name'}),
            'company': forms.Select(attrs={'class': 'form-control'})
        }
        
    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)  # Extract company context
        super().__init__(*args, **kwargs)

        if company:
            # If company is provided, exclude the 'company' field from the form and filter departments
            self.fields.pop('company')  # Remove company field from the form for company admin
        else:
            # If no company is provided, allow the user to select a company
            self.fields['company'].queryset = Company.objects.all()

        # Handle dynamic filtering of departments based on selected company in the form submission
        if 'company' in self.data:
            try:
                company_id = int(self.data.get('company'))
                self.fields['company'].queryset = Company.objects.filter(id=company_id)
            except (ValueError, TypeError):
                self.fields['company'].queryset = Company.objects.none()

       
class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ['name', 'company', 'department']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Role Name'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)  # Extract company context
        super().__init__(*args, **kwargs)
        
        if company:
            # If company is provided, exclude company field and filter departments
            self.fields.pop('company')
            self.fields['department'].queryset = Department.objects.filter(company=company)
        else:
            # If no company is provided, allow company selection and show no departments initially
            self.fields['company'].queryset = Company.objects.all()
            self.fields['department'].queryset = Department.objects.none()

        # If form is submitted, dynamically filter departments based on selected company
        if 'company' in self.data:
            try:
                company_id = int(self.data.get('company'))
                self.fields['department'].queryset = Department.objects.filter(company_id=company_id)
            except (ValueError, TypeError):
                self.fields['department'].queryset = Department.objects.none()

        
class CompanyProfileForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'address', 'contact_info','email','logo','company_code_for_employee_id']
        

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = Employee  # or Company if needed
        fields = ['name', 'email', 'phone_number', 'image']
        
        
class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ['title', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter announcement title'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter announcement content'}),
        }

class AttendanceCorrectionForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['clock_in', 'clock_out', 'status']
        widgets = {
            'clock_in': forms.TimeInput(attrs={'type': 'time'}),
            'clock_out': forms.TimeInput(attrs={'type': 'time'}),
        }
        
class LeaveRequestForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = ['leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Accept an additional argument for the employee or company if needed
        employee = kwargs.pop('employee', None)
        super().__init__(*args, **kwargs)

        if employee:
            # Filter leave types based on the company the employee belongs to
            self.fields['leave_type'].queryset = LeavePolicy.objects.filter(company=employee.company)
    
        
class LeavePolicyForm(forms.ModelForm):
    class Meta:
        model = LeavePolicy
        fields = ["leave_type", "max_days_per_year"] 