from rest_framework import viewsets
from .models import Company, Department, Role, Employee, Attendance, LeaveRequest, CustomUser ,Task,Announcement, LeavePolicy, LeaveBalance
from .serializers import CompanySerializer, DepartmentSerializer, RoleSerializer, EmployeeSerializer, AttendanceSerializer, LeaveSerializer
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseForbidden, HttpResponse, HttpResponseRedirect
from django.contrib.auth.decorators import user_passes_test, login_required
from rest_framework.permissions import IsAdminUser
from django.contrib import messages
from django.urls import reverse
from .forms import UserProfileForm, EmployeeForm, RoleForm, DepartmentForm,AnnouncementForm, AttendanceCorrectionForm, LeaveRequestForm, LeavePolicyForm
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse, HttpResponseBadRequest
from django.forms import modelform_factory
from django.db.models import Q, F
from django.core.mail import send_mail
import random , string,calendar
from django.db.models import Count
from datetime import datetime,timedelta
from django.utils.dateparse import parse_datetime
from django.db import IntegrityError



def is_company_admin(user):
    return user.user_type == "CompanyAdmin"


def home(request):
    return render(request, 'index.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user:
            login(request,user)
        

            try:
                # Fetch associated company and employee details, if available
                company = user.company  # Assuming CustomUser has a 'company' field
                employee = getattr(user, 'employee', None)  # Safe access to employee (if exists)

                # Set session data
                request.session["user_role"] = user.user_type
                request.session["company_id"] = company.id
                request.session["company_name"] = company.name

                if employee:
                    request.session["user_id"] = employee.id
                    request.session["user_department"] = employee.department.name
                else:
                    request.session["user_id"] = user.id  # Fallback for non-employee users

                return redirect("user_profile")  # Redirect to a common profile/dashboard
            except AttributeError:
                messages.error(request, "Error retrieving user or company details.")
                return redirect("login_view")
        else:
            # Invalid credentials
            messages.error(request, "Invalid username or password.")
            return redirect("login_view")

        print(request.session.get('user_role'))

    return render(request, "users/user_login.html")


def user_logout(request):
    logout(request)
    request.session.flush()
    return HttpResponseRedirect(reverse("login_view"))


def user_profile(request):
    # Fetch the logged-in user and session details
    user = request.user
    company_id = request.session.get("company_id")  # Company ID from session

    # Initialize variables
    employee = None
    role_name = None
    company = None

    try:
        # Fetch the employee details and associated company
        employee = Employee.objects.get(user=user, company_id=company_id)
        company = employee.company
        role_name = f"{employee.role.name} in {company.name}"
    except Employee.DoesNotExist:
        # For non-employee users (like Company Admin, HR)
        if user.user_type == 'Company Admin':
            role_name = f"Company Admin in {user.company.name}"
        elif user.user_type == 'HR':
            role_name = f"HR in {user.company.name}"
        elif user.user_type == 'Manager':
            role_name = f"Manager in {user.company.name}"
        else:
            role_name = f"Staff in {user.company.name}"

    if request.method == "POST":
        # Handle profile update logic for employees
        if employee:
            employee.name = request.POST.get("name", employee.name)
            employee.email = request.POST.get("email", employee.email)
            employee.phone_number = request.POST.get("phone", employee.phone_number)
            employee.address = request.POST.get("address", employee.address)
            if request.FILES.get("image"):
                employee.image = request.FILES.get("image")
            employee.save()

            messages.success(request, "Profile updated successfully!")
            return redirect("user_profile")

    context = {
        "user": user,
        "role_name": role_name,
        "company": company,
        "employee": employee,
    }
    return render(request, "users/user_profile.html", context)


def company_dashboard(request, company_id):
    # Fetch the company using the provided company_id
    company = get_object_or_404(Company, id=company_id)

    # Analytics
    total_employees = Employee.objects.filter(company=company).count()
    total_departments = Department.objects.filter(company=company).count()
    total_roles = Role.objects.filter(company=company).count()

    # Recent staff members
    recent_staff = Employee.objects.filter(company=company).order_by('-joining_date')[:5]

    # Attendance Statistics
    attendance_stats = {
        'present_count': Attendance.objects.filter(company=company, status='Present').count(),
        'absent_count': Attendance.objects.filter(company=company, status='Absent').count(),
        'late_count': Attendance.objects.filter(company=company, status='Late').count(),
    }

    # Leave Request Statistics
    leave_stats = {
        'pending_count': LeaveRequest.objects.filter(company=company, status='Pending').count(),
        'approved_count': LeaveRequest.objects.filter(company=company, status='Approved').count(),
        'rejected_count': LeaveRequest.objects.filter(company=company, status='Rejected').count(),
    }

    # Collect analytics in a dictionary
    analytics = {
        'total_employees': total_employees,
        'total_departments': total_departments,
        'total_roles': total_roles,
        'recent_staff': recent_staff,
    }

    # Render the dashboard template
    return render(
        request,
        'users/company_dashboard.html',
        {
            'company': company,
            'analytics': analytics,
            'attendance_stats': attendance_stats,
            'leave_stats': leave_stats,
        }
    )


def company_profile(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.session.get("user_role")
    user_id = request.session.get("user_id")

    if user_role == "Company Admin" and user_id == company_id:
        return render(request, 'users/company_admin/admin_company_profile.html', {'company': company})

    employee = Employee.objects.filter(id=user_id, company=company).first()
    if employee:
        return render(request, 'users/company_profile.html', {'company': company, 'employee': employee})

    return render(request, 'users/company_profile.html', {'company': company})


def add_staff_per_company(request):
    user_role = request.session.get("user_role")
    company_id = request.session.get("company_id")
    company = get_object_or_404(Company, id=company_id)

    # Define the EmployeeForm dynamically with filtered fields
    EmployeeForm = modelform_factory(
        Employee,
        fields=["name", "address", "phone_number", "role", "department", "salary", "status", "image", "joining_date", "email"],
    )

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save(commit=False)
            employee.company = company

            # Check for existing CustomUser
            if CustomUser.objects.filter(email=employee.email).exists():
                messages.error(request, "A user with this email already exists.")
                return render(request, "users/company_admin/add_staff.html", {"form": form, "company": company})

            # Map role name to user_type
            role_mapping = {"HR": 3, "Manager": 4}
            user_type = role_mapping.get(employee.role.name, 5)

            # Generate a secure random password
            random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # Create CustomUser
            user = CustomUser.objects.create_user(
                username=employee.email,
                password=random_password,
                first_name=employee.name,
                email=employee.email,
                user_type=user_type,
                company=company,
                role=employee.role,
                department=employee.department,
            )
            employee.user = user
            employee.save()

            # Send credentials via email
            send_mail(
                "Your Account Credentials",
                f"Hello {employee.name},\n\nYour account has been created.\nUsername: {employee.email}\nPassword: {random_password}\n\nBest regards,\nTeam",
                "amashiq310@gmail.com",
                [employee.email],
                fail_silently=False,
            )

            messages.success(request, "Staff member added successfully!")
            return redirect("view_staff_per_company", company_id=company.id)
        else:
            messages.error(request, "There was an error in the form. Please correct it.")
    else:
        form = EmployeeForm()

    # Filter dropdowns
    form.fields["role"].queryset = Role.objects.filter(company=company).exclude(name="Company Admin")
    form.fields["department"].queryset = Department.objects.filter(company=company).exclude(name="Admin")
    

    return render(request, "users/company_admin/add_staff.html", {"form": form, "company": company})

def view_staff_per_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    # Get all departments associated with the company
    departments = Department.objects.filter(company=company).exclude(name='Admin')
    
    # Handle department filter (if selected)
    selected_department = request.GET.get('department')
    if selected_department:
        staff_members = Employee.objects.filter(company=company, department_id=selected_department).exclude(role__name='Company Admin')
    else:
        staff_members = Employee.objects.filter(company=company).exclude(role__name='Company Admin')
    
    return render(
        request,
        "users/company_admin/view_staff.html",
        {
            "company": company,
            "departments": departments,
            "staff_members": staff_members,
            "selected_department": selected_department
        }
    )


def delete_staff_per_company(request, staff_id):
    try:
        # Ensure the user is logged in as a company admin
        user_role = request.session.get("user_role")
        company_id = request.session.get("company_id")

        # Retrieve the employee and ensure they belong to the current company
        employee = get_object_or_404(Employee, id=staff_id, company_id=company_id)

        # Retrieve the associated CustomUser
        user = employee.user

        # Delete the employee first
        employee.delete()

        # Then delete the associated CustomUser, ensuring it's linked and exists
        if user:
            user.delete()

        messages.success(request, "Staff member and associated user details deleted successfully.")
    except Exception as e:
        messages.error(request, f"An error occurred while deleting the staff member: {str(e)}")

    return redirect("view_staff_per_company", company_id=company_id)


def edit_staff_per_company(request, employee_id):
    # Retrieve the employee object or return a 404 if not found
    employee = get_object_or_404(Employee, id=employee_id)
    company = employee.company
    
    # If the request is POST, process the form
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        form.fields['company'].initial = company
        
        # Filter choices for role and department based on company and exclude invalid options
        form.fields["role"].queryset = Role.objects.filter(company=company).exclude(name="Company Admin")
        form.fields["department"].queryset = Department.objects.filter(company=company).exclude(name="Admin")
        
        if form.is_valid():
            form.save()  # Save the updated employee details
            return redirect('view_staff_per_company', company_id=company.id)  # Redirect to the staff list page after updating
    else:
        form = EmployeeForm(instance=employee)
        
        # Filter choices for role and department for the specific company
        form.fields["role"].queryset = Role.objects.filter(company=company).exclude(name="Company Admin")
        form.fields["department"].queryset = Department.objects.filter(company=company).exclude(name="Admin")
    
    # Render the template with the form
    return render(request, 'users/company_admin/edit_staff.html', {'form': form, 'employee': employee, 'company': company})



def role_management(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    # Fetch departments for filtering
    departments = company.departments.all().exclude(name="Admin")
    
    # Get the selected department from the request
    selected_department_id = request.GET.get('department')
    
    # Fetch roles and filter by department if selected
    if selected_department_id:
        roles = company.roles.filter(department_id=selected_department_id)
    else:
        roles = company.roles.all().exclude(name="Company Admin")
    
    # Check if the logged-in user is a "Company Admin" using the session
    user_role = request.session.get("user_role")
    is_company_admin = user_role == "Company Admin"  # Check if the session role is "Company Admin"

    context = {
        'company': company,
        'departments': departments,
        'roles': roles,
        'selected_department_id': selected_department_id,
        'is_company_admin': is_company_admin,  # Pass the result to the template
    }
    return render(request, 'users/company_admin/role_management.html', context)

def add_role_for_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == "POST":
        form = RoleForm(request.POST, company=company)  # Pass company context
        if form.is_valid():
            role = form.save(commit=False)
            role.company = company
            role.save()
            messages.success(request, "Role has been added successfully!")
            return redirect('role_management', company_id=company.id)
        else:
            messages.error(request, "Error: Please check the form fields.")
            print("Form errors:", form.errors)  # Debugging

    else:
        form = RoleForm(company=company)  # Pass company context

    departments = company.departments.all().exclude(name="Admin")  # Filter departments if needed

    context = {
        'form': form,
        'company': company,
        'departments': departments,
    }
    return render(request, 'users/company_admin/add_role.html', context)
    

def department_management(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    department = company.departments.all().exclude(name="Admin")
    user_role = request.session.get("user_role")
    is_company_admin = user_role == "Company Admin" 
    
    context={
        'company': company,
        'departments': department,
        'is_company_admin': is_company_admin
    }
    return render(request,'users/company_admin/department_management.html',context)

def add_department_for_company(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    
    if request.method == "POST":
        form = DepartmentForm(request.POST, company=company)  # Pass company context
        if form.is_valid():
            department = form.save(commit=False)
            department.company = company  # Assign the selected company to the department
            department.save()
            messages.success(request, "Department has been added successfully!")
            return redirect('department_management', company_id=company.id)
        else:
            messages.error(request, "Error: Please check the form fields.")
            print("Form errors:", form.errors)  # For debugging
    else:
        form = DepartmentForm(company=company)  # Pass company context

    context = {
        'form': form,
        'company': company,
    }

    return render(request, 'users/company_admin/add_department.html', context)

def delete_role_for_company(request, company_id, role_id):
    company = get_object_or_404(Company, id=company_id)
    role = get_object_or_404(Role, id=role_id, company=company)
    user_role = request.session.get("user_role")

    
    if request.method == "POST":
        role.delete()
        messages.success(request, "Role has been deleted successfully!")
        return redirect('role_management', company_id=company_id)
    
    context = {
        'company': company,
        'role': role,
    }
    return render(request, 'users/company_admin/delete_role.html', context)

def delete_department_for_company(request, company_id, department_id):
    company = get_object_or_404(Company, id=company_id)
    department = get_object_or_404(Department, id=department_id, company=company)
    user_role = request.session.get("user_role")
    
    if request.method == "POST":
        department.delete()
        messages.success(request, "Department has been deleted successfully!")
        return redirect('department_management', company_id=company_id)
    
    context = {
        'company': company,
        'department': department,
    }
    return render(request, 'users/company_admin/delete_department.html', context)
    

def attendance_dashboard(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.session.get("user_role")
    company_id = request.session.get('company_id')
    departments = Department.objects.filter(company=company).exclude(name="Admin")
    
    department_filter = request.GET.get('department')
    employee_filter = request.GET.get('employee')
    
    attendance_records = Attendance.objects.filter(company_id=company_id)
    
    if department_filter:
        attendance_records = attendance_records.filter(employee__department_id=department_filter)
        
    if employee_filter:
        attendance_records = attendance_records.filter(employee_id=employee_filter)
        
    employee_choices = Employee.objects.filter(
        company_id=company_id
    ).exclude(role__name="Company Admin").values('id', 'name', 'role__name')

    employee_list = [
        {'id': employee['id'], 'name_with_role': f"{employee['name']} ({employee['role__name']})"}
        for employee in employee_choices
    ]
    
    # Prepare calendar data as a list of days, not using `get()`
    calendar_data = []
    for record in attendance_records:
        calendar_data.append({
            'date': record.date,
            'employee': record.employee,
            'status': record.status,
        })

    # Creating a list of weeks (7 days each)
    days_of_month = sorted(set(record['date'] for record in calendar_data))
    week_rows = []
    for i in range(0, len(days_of_month), 7):
        week_rows.append(days_of_month[i:i+7])

    return render(request, 'users/company_admin/attendance_dashboard.html', {
        'attendance_records': attendance_records,
        'company': company,
        'company_id': company_id,
        'departments': departments,
        'employee_list': employee_list,
        'calendar_data': calendar_data,
        'week_rows': week_rows,  # Pass week_rows to template
    })



def leave_requests(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.session.get("user_role")
    leave_requests = LeaveRequest.objects.filter(company_id=company_id)
    company_id = request.session.get('company_id')
    
    return render (request, 'users/company_admin/leave_management.html',{
        'leave_requests': leave_requests,
        'company': company,
        'company_id': company_id,
    })
    
def manage_leave_request(request, leave_id, action):
    leave_request = get_object_or_404(LeaveRequest, id=leave_id)
    company = leave_request.company
    user_role = request.session.get("user_role")
    company_id = request.session.get('company_id')
    
    if action == 'approve':
        leave_request.status = 'Approved'
    elif action == 'reject':
        leave_request.status = 'Rejected'
        
    leave_request.save()
    
    return redirect(reverse('leave_requests'))



def create_leave_policy(request, company_id):
    # Retrieve the company object
    company = get_object_or_404(Company, id=company_id)

    if request.method == "POST":
        form = LeavePolicyForm(request.POST)
        if form.is_valid():
            leave_policy = form.save(commit=False)
            leave_policy.company = company  # Associate the leave policy with the company
            try:
                leave_policy.save()
                messages.success(request, "Leave policy created successfully.")
                return redirect("list_leave_policies",company_id=company.id)  # Update with your actual URL name
            except Exception as e:
                messages.error(request, f"Error creating leave policy: {str(e)}")
        else:
            messages.error(request, "Invalid form submission. Please check the input.")
    else:
        form = LeavePolicyForm()

    return render(
        request, 
        "users/hr/leave_policy_form.html", 
        {"form": form, "company": company}
    )

def list_leave_policies(request,company_id):
    company = get_object_or_404(Company, id=company_id)
    policies = LeavePolicy.objects.select_related("company").all()
    return render(request, "users/hr/leave_policy_list.html", {"policies": policies,'company':company})


# Delete a leave policy
def delete_leave_policy(request, policy_id, company_id):
    # Retrieve the leave policy object
    policy = get_object_or_404(LeavePolicy, id=policy_id)
    company = get_object_or_404(Company, id=company_id)

    user_company_id = request.session.get("company_id")

    # Check if the request method is POST to confirm deletion
    if request.method == "POST":
        try:
            policy.delete()  # Delete the leave policy
            messages.success(request, "Leave policy deleted successfully.")
        except Exception as e:
            messages.error(request, f"Error deleting leave policy: {str(e)}")
        return redirect('list_leave_policies', company_id=company_id)

    # Render a confirmation page
    return render(request, "users/hr/confirm_delete_leave_policy.html", {"policy": policy, "company": company})


def manager_dashboard(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.session.get("user_role")
    company_id = request.session.get('company_id')
    employee = get_object_or_404(Employee, user=request.user, company=company)
    
    manager = get_object_or_404(Employee, user=request.user, company=company)
    department = manager.department
    total_employees_in_department = Employee.objects.filter(department=department , company=company).count()
    total_attendance_in_department = Attendance.objects.filter(employee__department=department).count()
    
    attendance_stats = Attendance.objects.filter(employee__department=department).values('status').annotate(count=Count('status'))
    
    leave_stats = LeaveRequest.objects.filter(employee__department=department).values('status').annotate(count=Count('status'))
    
    context = {
        'company': company,
        'employee': employee,
        'manager': manager,
        'company_id': company_id,
        'department': department,
        'total_employees_in_department': total_employees_in_department,
        'total_attendance_in_department': total_attendance_in_department,
        'attendance_stats': attendance_stats,
        'leave_stats': leave_stats,
        
    }
    
    return render(request, 'users/manager/manager_dashboard.html', context)



def manage_attendance(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.user.employee.role
    manager = get_object_or_404(Employee, user=request.user, company=company)
    department = manager.department

    common_holidays = [
        {'name': 'New Year', 'date': '2024-01-01', 'color': '#ff0000'},
        {'name': 'Independence Day', 'date': '2024-08-15', 'color': '#ff0000'},
        {'name': 'Christmas', 'date': '2024-12-25', 'color': '#ff0000'},
    ]

    if request.method == "POST":
        selected_date = request.POST.get("date")
        
        # Loop through each employee in the department and update their attendance
        for employee in department.employees.all():  # Use department.employee_set
            clock_in = request.POST.get(f"clock_in_{employee.id}")
            clock_out = request.POST.get(f"clock_out_{employee.id}")
            status = request.POST.get(f"status_{employee.id}")
            
            clock_in_datetime = None
            clock_out_datetime = None

            if clock_in:
                clock_in_datetime = datetime.strptime(f"{selected_date} {clock_in}", "%Y-%m-%d %H:%M")
            if clock_out:
                clock_out_datetime = datetime.strptime(f"{selected_date} {clock_out}", "%Y-%m-%d %H:%M")

            Attendance.objects.update_or_create(
                employee=employee,
                date=selected_date,
                defaults={
                    "clock_in": clock_in_datetime,
                    "clock_out": clock_out_datetime,
                    "status": status,
                    "company": company,
                }
            )

        messages.success(request, "Attendance updated successfully.")
        return redirect('manage_attendance', company_id=company.id)

    # Fetch attendance records for the manager's department
    attendance_records = Attendance.objects.filter(employee__department=department)

    context = {
        'company': company,
        'manager': manager,
        'attendance_records': attendance_records,
        'common_holidays': common_holidays,
        'department': department,
        'employees': department.employees.all(),  # Pass employees to the template
    }

    return render(request, 'users/manager/manage_attendance.html', context)

def get_employees_by_date(request, company_id):
    if request.method == "GET" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        selected_date = request.GET.get("date")
        company = get_object_or_404(Company, id=company_id)
        manager = get_object_or_404(Employee, user=request.user, company=company)
        department = manager.department

        # Get employees for the manager's department
        employees = Employee.objects.filter(department=department, company=company)

        # Get attendance records for selected date
        attendance_records = Attendance.objects.filter(employee__in=employees, date=selected_date)

        employee_data = []
        for employee in employees:
            attendance = attendance_records.filter(employee=employee).first()
            employee_data.append({
                "id": employee.id,
                "name": employee.name,
                "role": employee.role.name,
                "status": attendance.status if attendance else "Absent",
            })

        return JsonResponse({"employees": employee_data})




def manage_leave_requests(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.session.get("user_role")

    manager = get_object_or_404(Employee, user=request.user, company=company)
    department = manager.department


    leave_requests = LeaveRequest.objects.filter(employee__department=department, company=company)

    if request.method == "POST":
        leave_request_id = request.POST.get("leave_request_id")
        action = request.POST.get("action")
        leave_request = get_object_or_404(LeaveRequest, id=leave_request_id)

        # Approve or reject the leave request
        if action == "approve":
            leave_request.status = "Approved"
            # Update leave balance after approval
            leave_balance = get_object_or_404(LeaveBalance, employee=leave_request.employee, leave_type=leave_request.leave_type)
            days_requested = (leave_request.end_date - leave_request.start_date).days + 1
            if leave_balance.remaining_days >= days_requested:
                leave_balance.remaining_days -= days_requested
                leave_balance.save()
            else:
                messages.error(request, "Insufficient leave balance.")
                leave_request.status = "Pending"
                leave_request.save()
                return redirect('manage_leave_requests', company_id=company.id)
        elif action == "reject":
            leave_request.status = "Rejected"
        
        leave_request.save()
        messages.success(request, f"Leave request {action}d successfully.")
        return redirect('manage_leave_requests', company_id=company.id)

    context = {
        'company': company,
        'leave_requests': leave_requests,
    }

    return render(request, 'users/manager/manage_leave_requests.html', context)

def manage_attendance_hr(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    if request.method == "POST":
        selected_date = request.POST.get("date")
        
        # Loop through all employees in the company and update their attendance
        for employee in company.employees.all():
            clock_in = request.POST.get(f"clock_in_{employee.id}")
            clock_out = request.POST.get(f"clock_out_{employee.id}")
            status = request.POST.get(f"status_{employee.id}")
            
            # Set default status if not provided
            if not status:
                status = 'Absent'

            clock_in_datetime = None
            clock_out_datetime = None

            if clock_in:
                clock_in_datetime = datetime.strptime(f"{selected_date} {clock_in}", "%Y-%m-%d %H:%M")
            if clock_out:
                clock_out_datetime = datetime.strptime(f"{selected_date} {clock_out}", "%Y-%m-%d %H:%M")

            # Update or create the attendance record
            Attendance.objects.update_or_create(
                employee=employee,
                date=selected_date,
                defaults={
                    "clock_in": clock_in_datetime,
                    "clock_out": clock_out_datetime,
                    "status": status,
                    "company": company,
                }
            )

        messages.success(request, "Attendance updated successfully.")
        return redirect('manage_attendance_hr', company_id=company.id)

    # Fetch attendance records for all employees in the company
    attendance_records = Attendance.objects.filter(company=company).exclude(employee__role__name="Company Admin")

    context = {
        'company': company,
        'attendance_records': attendance_records,
        'employees': company.employees.all(),  # Pass all employees to the template
    }

    return render(request, 'users/hr/manage_attendance_hr.html', context)


def get_employees_by_date_hr(request, company_id):
    if request.method == "GET" and request.headers.get("x-requested-with") == "XMLHttpRequest":
        selected_date = request.GET.get("date")
        company = get_object_or_404(Company, id=company_id)

        # Get all employees for the company
        employees = Employee.objects.filter(company=company).exclude(role__name="Company Admin")

        # Get attendance records for the selected date
        attendance_records = Attendance.objects.filter(employee__in=employees, date=selected_date)

        employee_data = []
        for employee in employees:
            attendance = attendance_records.filter(employee=employee).first()
            employee_data.append({
                "id": employee.id,
                "name": employee.name,
                "role": employee.role.name,  # Include role name
                "status": attendance.status if attendance else "Absent",
            })

        return JsonResponse({"employees": employee_data})
    
    


def manage_tasks(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.user.employee.role
    manager = get_object_or_404(Employee, user=request.user, company=company)
    department = manager.department
    employees = Employee.objects.filter(company=company, department=department)
    # Fetch tasks for the manager's department only
    tasks = Task.objects.filter(company=company, assigned_to__department=department)

    if request.method == "POST":
        task_name = request.POST.get("task_name")
        description = request.POST.get("description")
        deadline = request.POST.get("deadline")
        assigned_to_id = request.POST.get("assigned_to")
        assigned_to = get_object_or_404(Employee, id=assigned_to_id, department=department, company=company)

        # Create the task and assign it to an employee within the same department
        Task.objects.create(
            task_name=task_name,
            description=description,
            deadline=deadline,
            assigned_to=assigned_to,
            company=company,
        )

        messages.success(request, "Task added successfully.")
        return redirect("manage_tasks", company_id=company.id)

    # Get the employees of the same department as the logged-in manager for task assignment
    
    
    context = {
        "company": company,
        "tasks": tasks,  # Filtered tasks for the department
        "department": department,
        "employees": employees,  # Employees in the department
    }

    return render(request, "users/manager/manage_tasks.html", context)



def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    company_id = task.company.id  # Assuming the task has a related company
    task.delete()
    return redirect('manage_tasks', company_id=company_id)


def view_department_employees(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    user_role = request.session.get("user_role")

    # Get the manager and their department
    manager = get_object_or_404(Employee, user=request.user, company=company)
    department = manager.department

    # Fetch employees in the same department
    employees = Employee.objects.filter(department=department, company=company)

    context = {
        "company": company,
        "department": department,
        "employees": employees,
    }

    return render(request, "users/manager/view_department_employees.html", context)


def list_announcements(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    announcements = Announcement.objects.filter(company=company).order_by('-created_at')
    context = {
        "company": company,
        "announcements": announcements,
    }
    return render(request, "users/manager/list_announcements.html", context)


def create_announcement(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.company = company
            announcement.save()
            messages.success(request, "Announcement created successfully.")
            return redirect('list_announcements', company_id=company.id)
    else:
        form = AnnouncementForm()

    context = {
        "company": company,
        "form": form,
    }
    return render(request, "users/manager/create_announcement.html", context)


def edit_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    if request.method == "POST":
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            form.save()
            messages.success(request, "Announcement updated successfully.")
            return redirect('list_announcements', company_id=announcement.company.id)
    else:
        form = AnnouncementForm(instance=announcement)

    context = {
        "form": form,
        "announcement": announcement,
    }
    return render(request, "users/manager/edit_announcement.html", context)


def delete_announcement(request, announcement_id):
    announcement = get_object_or_404(Announcement, id=announcement_id)
    company_id = announcement.company.id
    announcement.delete()
    messages.success(request, "Announcement deleted successfully.")
    return redirect('list_announcements', company_id=company_id)

def view_attendance(request,company_id):
    company = get_object_or_404(Company, id=company_id)
    employee = Employee.objects.get(user=request.user)
    attendances = Attendance.objects.filter(employee=employee).order_by('-date')

    return render(request, 'users/employee/view_attendance.html', {'attendances': attendances, 'company':company})


def request_correction(request, attendance_id, company_id):
    company = get_object_or_404(Company, id=company_id)
    attendance = Attendance.objects.get(id=attendance_id)

    if attendance.correction_requested:
        # If a correction is already requested, we can show a message or redirect
        return redirect('attendance:view_attendance')

    if request.method == 'POST':
        form = AttendanceCorrectionForm(request.POST, instance=attendance)
        if form.is_valid():
            attendance.correction_requested = True
            attendance.save()
            return redirect('attendance:view_attendance')
    else:
        form = AttendanceCorrectionForm(instance=attendance)

    return render(request, 'users/employee/request_correction.html', {'form': form, 'attendance': attendance, 'company':company})


def approve_correction(request, attendance_id):
    attendance = Attendance.objects.get(id=attendance_id)
    if not attendance.correction_requested:
        raise Http404("No correction request found.")

    if request.method == 'POST':
        attendance.correction_approved = True
        attendance.save()
        return redirect('view_attendance')

    return render(request, 'users/employee/approve_correction.html', {'attendance': attendance})


def submit_leave_request(request, company_id):
    company = get_object_or_404(Company, id=company_id)

    if request.method == 'POST':
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave_request = form.save(commit=False)
            leave_request.employee = request.user.employee
            leave_request.company = company
            leave_request.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect('view_leave_requests', company_id=company_id)
    else:
        form = LeaveRequestForm()
        # Set the queryset for leave_type dynamically based on the company
        form.fields['leave_type'].queryset = LeavePolicy.objects.filter(company=company)

    context = {
        'form': form,
        'company': company,
    }

    return render(request, 'users/employee/submit_leave_request.html', context)

def view_leave_requests(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    leave_requests = LeaveRequest.objects.filter(employee=request.user.employee)
    
    # Example of reverse usage:
    url = reverse('view_leave_requests', kwargs={'company_id': company.id})
    print(url)  # Debugging output, will print the generated URL
    
    return render(request, 'users/employee/view_leave_requests.html', {'leave_requests': leave_requests, 'company': company})

def update_leave_requests(request, pk, company_id):
    company = get_object_or_404(Company, id=company_id)
    leave_request = get_object_or_404(LeaveRequest, pk=pk, employee=request.user.employee, status="Pending")
    if request.method == "POST":
        form = LeaveRequestForm(request.POST, instance=leave_request)
        if form.is_valid():
            form.save()
            messages.success(request, "Leave Request Updated Successfully.")
            # Correct way to redirect with company_id
            return redirect('view_leave_requests', company_id=company_id)
    else:
        form = LeaveRequestForm(instance=leave_request)
    return render(request, 'users/employee/update_leave_request.html', {'form': form, 'company': company})


def view_leave_policy_per_company (request, company_id):
    # Fetch the company based on the provided ID
    company = get_object_or_404(Company, id=company_id)

    # Fetch leave policies associated with the company
    leave_policies = LeavePolicy.objects.filter(company=company)

    context = {
        "company": company,
        "leave_policies": leave_policies,
    }

    return render(request, "users/employee/view_leave_policy.html", context)
    
def view_leave_balances(request,company_id):
    company = get_object_or_404(Company, id=company_id)
    employee = Employee.objects.get(user=request.user)


    leave_balance = LeaveBalance.objects.filter(employee=employee).first()

    return render(request, 'users/employee/view_leave_balances.html', {
        'leave_balance': leave_balance,
        'company': company
    })
    

def view_tasks(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    employee = get_object_or_404(Employee, user=request.user, company=company)
    tasks = Task.objects.filter(assigned_to=employee)
    return render(request, 'users/employee/tasks.html', {'tasks': tasks, 'company': company})

def update_task_status(request,task_id,company_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user.employee)
    company = get_object_or_404(Company, id=company_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [choice[0] for choice in Task.STATUS_CHOICES]:
            task.status = new_status
            task.save()
            return redirect('view_tasks',company_id=company.id)
    return render(request, 'users/employee/update_task.html', {'task': task,'company':company})

def view_announcements(request, company_id):
    company = get_object_or_404(Company, id=company_id)
    employee = get_object_or_404(Employee, user=request.user, company=company)
    announcements = Announcement.objects.filter(company=company)
    return render(request, 'users/employee/announcements.html', {'announcements': announcements, 'company': company})

    


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [IsAdminUser]  # Only admins can access this viewset


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()
    serializer_class = AttendanceSerializer


class LeaveViewSet(viewsets.ModelViewSet):
    queryset = LeaveRequest.objects.all()
    serializer_class = LeaveSerializer
