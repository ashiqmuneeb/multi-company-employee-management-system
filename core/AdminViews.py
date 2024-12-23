from django.shortcuts import render, HttpResponseRedirect, get_object_or_404 ,redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView
from core.models import Company, Role, Employee, Department,CustomUser,Attendance,LeaveRequest
from django.contrib.auth.models import User, Group
from django.utils.decorators import method_decorator
from django.urls import reverse_lazy,reverse
from django.contrib import messages
from django.core.paginator import Paginator
import string
import random
from .forms import CompanyForm,DepartmentForm,EmployeeForm, RoleForm
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.db.models import Count, Q
from django.contrib.auth import authenticate,login,logout


def is_admin(user):
    return user.is_superuser or user.user_type == "Admin"

User = get_user_model()


def company_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        # Check if user exists and is a superuser
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect(reverse('dashboard'))

        messages.error(request, 'Invalid credentials or access restricted to admin only.')
        return render(request, 'company/login.html')
    
    return render(request, 'company/login.html')

@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def company_manage_dashboard(request):
    # Aggregating company and employee data
    total_companies = Company.objects.count()

    # Aggregating employee count per company (where employees belong to a company)
    total_staff = Employee.objects.count()

    # Aggregating attendance statistics across all companies
    attendance_stats = Attendance.objects.values('company').annotate(
        present_count=Count('status', filter=Q(status='Present')),
        absent_count=Count('status', filter=Q(status='Absent')),
        late_count=Count('status', filter=Q(status='Late')),
    )

    # Aggregating leave statistics across all companies
    leave_stats = LeaveRequest.objects.values('company').annotate(
        pending_count=Count('status', filter=Q(status='Pending')),
        approved_count=Count('status', filter=Q(status='Approved')),
        rejected_count=Count('status', filter=Q(status='Rejected')),
    )

    # Employee count for each company
    company_data = Company.objects.annotate(employee_count=Count('employees'))

    # Fetch all companies for displaying their details
    all_companies = Company.objects.all()

    # Prepare context to pass to the template
    context = {
        "total_companies": total_companies,
        "total_staff": total_staff,
        "attendance_stats": attendance_stats,
        "leave_stats": leave_stats,
        "company_data": company_data,
        "all_companies": all_companies,  # Add all companies to the context
    }

    return render(request, "company/dashboard.html", context)


@method_decorator([login_required(login_url="/company-login/"), user_passes_test(is_admin)], name='dispatch')
class CompanyListView(ListView):
    model = Company
    template_name = "company/company_list.html"
    context_object_name = "list_company"
    paginate_by = 10

    def get_queryset(self):
        return Company.objects.all().order_by('name')


def create_company(request):
    company_code = None  # Default to None for company code initially
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the company instance (this will automatically generate the company code)
            company = form.save()

            # Get the admin username and password from the form
            admin_username = request.POST.get('admin_username')
            admin_password = request.POST.get('admin_password')

            if admin_username and admin_password:
                # Check if the username already exists
                if CustomUser.objects.filter(username=admin_username).exists():
                    messages.error(request, 'Admin username already exists. Please choose a different username.')
                    return redirect('create_company')

                # Create the CustomUser for the company admin (CompanyAdmin role)
                admin_user = CustomUser.objects.create_user(
                    username=admin_username,
                    password=admin_password,
                    user_type=2,  # CompanyAdmin (user_type=2)
                    is_staff=True,
                    company=company
                )

                # Save the company with the generated company code
                company_code = company.company_code_for_employee_id  # This is automatically set by the model
                company.save()

                messages.success(request, 'Company created successfully.')
                return redirect('list_company')  # Redirect to company listing
            else:
                messages.error(request, 'Admin username and password are required.')
        else:
            messages.error(request, 'There was an error creating the company.')
    else:
        form = CompanyForm()

    # Pass the company_code to the template to display it after the company is saved
    return render(request, 'company/company_create.html', {
        'form': form,
        'company_code': company_code  # Pass the generated company code to the template
    })

    
    
class CompanyDetailView(DetailView):
    model = Company
    template_name = "company/company_detail.html"
    context_object_name = "company"
    
@method_decorator([login_required(login_url="/company-login/"), user_passes_test(is_admin)], name='dispatch')
class CompanyUpdateView(UpdateView):
    model = Company
    fields = ['name', 'address', 'contact_info', 'logo','email']
    template_name = "company/company_update.html"
    success_url = reverse_lazy('list_company')
    
@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def update_company_list(request):
    companies = Company.objects.all()
    return render(request, "company/update_company_list.html", {'companies': companies})

@method_decorator([login_required(login_url="/company-login/"), user_passes_test(is_admin)], name='dispatch')
class CompanyDeleteView(DeleteView):
    model = Company
    template_name = 'company/company_confirm_delete.html'
    success_url = reverse_lazy('list_company')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        
        
        if hasattr(self.object, 'staff_members'):
            company_admins = self.object.staff_members.all()
            for admin in company_admins:
                admin.delete()
        
        # Delete all related employees and their users
        employees = self.object.employees.all()  # Fetch all employees linked to the company
        for employee in employees:
            if employee.user:  # If employee has an associated user
                employee.user.delete()  # Delete the CustomUser
            employee.delete()  # Delete the employee record

        # Delete the company itself
        self.object.delete()

        # Display a success message
        messages.success(request, f'Company "{self.object.name}" and all associated staff have been deleted.')

        return super().delete(request, *args, **kwargs)
    
def company_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse("home"))
  
@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def add_staff(request):
    companies = Company.objects.all()

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            employee = form.save(commit=False)
            role = form.cleaned_data.get('role')
            company_id = form.cleaned_data.get('company')

            # Validate company
            if not company_id:
                messages.error(request, "Please select a company.")
                return redirect('add_staff')
            
            try:
                company = Company.objects.get(id=company_id.id)
                employee.company = company
            except Company.DoesNotExist:
                messages.error(request, "Selected company does not exist.")
                return redirect('add_staff')

            # Map role to user_type
            user_type_mapping = {
                'Admin': 1,
                'Company Admin': 2,
                'HR': 3,
                'Manager': 4,
            }
            user_type = user_type_mapping.get(role.name if role else None, 5)

            # Check if the email is already in use by another user
            if CustomUser.objects.filter(username=employee.email).exists():
                messages.error(request, "This email is already in use for another user.")
                return redirect('add_staff')

            # If the role is Company Admin, handle it differently
            if role.name == "Company Admin":
                # Check if a Company Admin already exists for this company
                existing_admin = CustomUser.objects.filter(user_type=2, company=company).first()

                if existing_admin:
                    # If a Company Admin already exists, update their details
                    existing_admin.first_name = employee.name
                    existing_admin.email = employee.email
                    existing_admin.role = role
                    existing_admin.department = employee.department  # Optional: update department
                    existing_admin.save()

                    # Link the existing CustomUser with the Employee model
                    employee.user = existing_admin
                else:
                    # Create the CustomUser for the Company Admin if not already exists
                    custom_user = CustomUser.objects.create_user(
                        username=employee.email,
                        password=employee.phone_number,  # Consider hashing or generating a random password
                        user_type=user_type,
                        company=company,
                    )
                    # Set additional fields
                    custom_user.first_name = employee.name
                    custom_user.email = employee.email
                    custom_user.role = role
                    custom_user.department = employee.department
                    custom_user.save()

                    # Link the created CustomUser with the Employee model
                    employee.user = custom_user

            # Generate employee ID
            employee.employee_id = employee.generate_employee_id()
            employee.save()

            messages.success(request, "Staff member added successfully!")
            return redirect('view_staff')
        else:
            messages.error(request, "Please fix the errors in the form.")
    else:
        form = EmployeeForm()

    return render(request, 'company/add_staff.html', {
        'form': form,
        'companies': companies,
        'statuses': Employee.STATUS_CHOICES,
    })

 


@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def view_staff(request):
    selected_company = request.GET.get('company')  # Get the selected company from the GET request
    employees = Employee.objects.none()  # Default value, in case no company is selected
    
    if selected_company:
        employees = Employee.objects.filter(company_id=selected_company)
    
    # You might want to send all companies for the dropdown
    companies = Company.objects.all()
    
    return render(request, 'company/staff_management.html', {
        'employees': employees,
        'companies': companies,
        'selected_company': selected_company,
    })
    
   
@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def staff_details(request, id):
    # Get employee details
    employee = get_object_or_404(Employee, id=id)

    return render(request, 'company/staff_details.html', {
        'employee': employee
    })
    
@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def edit_staff(request, id):
    # Get the employee object
    employee = get_object_or_404(Employee, id=id)
    

    companies = Company.objects.all()
    departments = Department.objects.filter(company=employee.company)
    roles = Role.objects.filter(company=employee.company)
   
    
    if request.method == 'POST':
        # Extract form data
        name = request.POST.get('name')
        address = request.POST.get('address')
        phone_number = request.POST.get('phone_number')
        joining_date = request.POST.get('joining_date')
        salary = request.POST.get('salary')
        status = request.POST.get('status')
        company_id = request.POST.get('company')
        department_id = request.POST.get('department')
        role_id = request.POST.get('role')
        image = request.FILES.get('image')
        
        # Validate required fields
        if not company_id:
            messages.error(request, "Please select a company.")
            return redirect('edit_staff', id=id)
        
        # Fetch the company
        try:
            company = Company.objects.get(id=company_id)
            department = Department.objects.get(id=department_id,company=company)
            role = Role.objects.get(id=role_id,company=company)
        except Company.DoesNotExist:
            messages.error(request, "Selected company does not exist.")
            return redirect('edit_staff', id=id)
        
        # Handle department and role
        
        # Update the employee object
        employee.name = name
        employee.address = address
        employee.phone_number = phone_number
        employee.joining_date = joining_date
        employee.salary = salary
        employee.status = status
        employee.company = company
        employee.department = department
        employee.role = role
        employee.image = image if image else employee.image  

        
        
        # Save the updated employee object
        employee.save()

        messages.success(request, 'Staff member updated successfully!')
        return redirect('view_staff')

    # If GET request, prepare the data for rendering the form
    return render(request, 'company/edit_staff.html', {
        'employee': employee,
        'companies': companies,
        'statuses': Employee.STATUS_CHOICES,
        'department_choices': departments,
        'role_choices': roles,
    })
    
@login_required
@user_passes_test(is_admin)
def delete_staff(request):
    company_id = request.GET.get('company')  # Get selected company from query params
    companies = Company.objects.all()  # List all companies
    employees = Employee.objects.all()

    if company_id:
        employees = employees.filter(company_id=company_id)  # Filter employees by company ID

    # Add pagination
    paginator = Paginator(employees, 10)  # Show 10 employees per page
    page = request.GET.get('page')
    employees = paginator.get_page(page)

    context = {
        'companies': companies,
        'employees': employees,
        'selected_company': company_id,
    }
    return render(request, 'company/delete_staff.html', context)

@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def delete_staff_confirmation(request, id):
    employee = get_object_or_404(Employee, id=id)

    if request.method == 'POST':
        # Optionally delete any other related records (if applicable) before deleting the user
        if employee.user:
            employee.user.delete()  # This deletes the related CustomUser
        
        # Delete the employee record itself
        employee.delete()

        messages.success(request, f'Employee {employee.name} has been deleted successfully.')
        return redirect('view_staff')  # Redirect to the staff list page

    return render(request, 'company/confirm_delete_staff.html', {'employee': employee})

@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def add_department(request):
    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('add_department')  # Redirect to a department listing page
    else:
        form = DepartmentForm()
    
    return render(request, 'company/add_department.html', {'form': form})
        
@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def department_list(request):
    selected_company_id = request.GET.get('company')
    departments = Department.objects.all()

    # Filter by company if a specific company is selected
    if selected_company_id:
        departments = departments.filter(company_id=selected_company_id)

    companies = Company.objects.all()  # Fetch all companies for the dropdown

    return render(request, 'company/department_list.html', {
        'departments': departments,
        'companies': companies,
        'selected_company_id': selected_company_id,
    })
    
def edit_delete_department(request):
    departments = Department.objects.all()
    return render(request, 'company/edit_delete_department.html', {'departments': departments})

def edit_department(request, department_id):
    # Get the department to edit
    department = get_object_or_404(Department, id=department_id)
    
    # Check if the method is POST (for form submission)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, 'Department updated successfully.')
            return redirect('department_list')  # Redirect to the department list page
    else:
        form = DepartmentForm(instance=department)

   
    return render(request, 'company/edit_department.html', {'form': form, 'department': department})

def delete_department(request, department_id):

    department = get_object_or_404(Department, id=department_id)
    
    
    if request.method == 'POST':
        department.delete()
        messages.success(request, 'Department deleted successfully.')
        return redirect('department_list')  
    
    return render(request, 'company/delete_department.html', {'department': department})

@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def add_role(request):
    if request.method == "POST":
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Role added successfully.")
            return redirect('add_role')  # Redirect to the same page or another page
        else:
            messages.error(request, "Error: Please check the form fields.")
            print(form.errors)  # Debug the form errors
    else:
        form = RoleForm()

    return render(request, 'company/add_role.html', {'form': form})


def get_departments(request):
    company_id = request.GET.get('company_id')
    if company_id:
        departments = Department.objects.filter(company_id=company_id).values('id', 'name')
        return JsonResponse(list(departments), safe=False)
    return JsonResponse({'error': 'Invalid company ID'}, status=400)


@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def role_list(request):
    selected_company_id = request.GET.get('company')
    roles = Role.objects.all()

    if selected_company_id:
        roles = roles.filter(company_id=selected_company_id)

    companies = Company.objects.all()  

    return render(request, 'company/role_list.html', {
        'roles': roles,
        'companies': companies,
        'selected_company_id': selected_company_id,
    })
    
def edit_delete_role(request):
    roles = Role.objects.all()
    return render(request, 'company/edit_delete_role.html', {'roles': roles})


@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def edit_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)
        if form.is_valid():
            form.save()
            messages.success(request, "Role updated successfully.")
            return redirect('role_list')
    else:
        form = RoleForm(instance=role)
    
    return render(request, 'company/edit_role.html', {'form': form, 'role': role})


@login_required(login_url="/company-login/")
@user_passes_test(is_admin)
def delete_role(request, role_id):
    role = get_object_or_404(Role, id=role_id)
    
    if request.method == 'POST':
        role.delete()
        messages.success(request, "Role deleted successfully.")
        return redirect('role_list')
    
    return render(request, 'company/delete_role.html', {'role': role})

def load_departments_and_roles(request):
    company_id = request.GET.get('company_id')  
    departments = Department.objects.filter(company_id=company_id)
    roles = Role.objects.filter(company_id=company_id)

    
    department_data = [{"id": department.id, "name": department.name} for department in departments]
    role_data = [{"id": role.id, "name": role.name} for role in roles]

    return JsonResponse({
        'departments': department_data,
        'roles': role_data
    })
    
    
