from django.urls import path, include
from . import views,AdminViews
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, DepartmentViewSet, RoleViewSet, EmployeeViewSet, AttendanceViewSet, LeaveViewSet
from django.contrib.auth import views as auth_views

router = DefaultRouter()
router.register(r'companies', CompanyViewSet)
router.register(r'departments', DepartmentViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'employees', EmployeeViewSet)
router.register(r'attendance', AttendanceViewSet)
router.register(r'leaves', LeaveViewSet)


urlpatterns = [
    path('api/', include(router.urls)),
    path('',views.home, name='home'),
    path('login-view/', views.login_view, name='login_view'),
    path('user-profile/',views.user_profile, name='user_profile'),
    path('company/<int:company_id>/dashboard/', views.company_dashboard, name='company_dashboard'),
    path('company/<int:company_id>/profile/',views.company_profile, name='company_profile'),
    path('user-logout/',views.user_logout, name='user_logout'),
    
    
    #administrator
    #company managment
    path('login/',AdminViews.company_login_view,name='login_company'),
    path('dashboard/', AdminViews.company_manage_dashboard, name='dashboard'), 
    path('logout/',AdminViews.company_logout,name='logout_company'),
    path('company-list/',AdminViews.CompanyListView.as_view(),name='list_company'),
    path('company-create/', AdminViews.create_company, name='create_company'),
    path('company/<int:pk>/', AdminViews.CompanyDetailView.as_view(), name='company_detail'),
    path('company-update-list/', AdminViews.update_company_list, name='update_company_list'),
    path('company-update/<int:pk>/', AdminViews.CompanyUpdateView.as_view(), name='update_company'),  
    path('company-delete/<int:pk>/', AdminViews.CompanyDeleteView.as_view(), name='delete_company'),
    
   #staff Managment
    path('add-staff/', AdminViews.add_staff, name='add_staff'),
    path('view-staff/', AdminViews.view_staff, name='view_staff'),
    path('staff-details/<int:id>/', AdminViews.staff_details, name='staff_details'),
    path('edit-staff/<int:id>/', AdminViews.edit_staff, name='edit_staff'),
    path('delete-staff/', AdminViews.delete_staff, name='delete_staff'),
    path('delete-staff/<int:id>/confirm/', AdminViews.delete_staff_confirmation, name='delete_staff_confirmation'),
    path('load-departments-and-roles/', AdminViews.load_departments_and_roles, name='load_departments_and_roles'),
    
    #Departement Management
    path('add-department/', AdminViews.add_department, name='add_department'),
    path('departments/', AdminViews.department_list, name='department_list'),
    path('edit-delete-department/', AdminViews.edit_delete_department, name='edit_delete_department'),
    path('edit-department/<int:department_id>/', AdminViews.edit_department, name='edit_department'),
    path('delete-department/<int:department_id>/', AdminViews.delete_department, name='delete_department'),
    
    #Role Management
    path('add-role/', AdminViews.add_role, name='add_role'),
    path('roles/', AdminViews.role_list, name='role_list'),
    path('edit-delete-role/', AdminViews.edit_delete_role, name='edit_delete_role'),
    path('roles/edit/<int:role_id>/', AdminViews.edit_role, name='edit_role'),
    path('roles/delete/<int:role_id>/', AdminViews.delete_role, name='delete_role'),
    path('get-departments/', AdminViews.get_departments, name='get_departments'),
    
    
    #Company Admin and HR
    path('company-add_staff/', views.add_staff_per_company , name='add_staff_per_company'),
    path('company-view-staff/<int:company_id>/', views.view_staff_per_company, name='view_staff_per_company'),
    path("delete-staff/<int:staff_id>/", views.delete_staff_per_company, name="delete_staff_per_company"),
    path('edit_staff/<int:employee_id>/', views.edit_staff_per_company, name='edit_staff_per_company'),
    path('company/<int:company_id>/role-management/', views.role_management, name='role_management'),
    path('company/<int:company_id>/add-role-company/', views.add_role_for_company , name='add_role'),
    path('company/<int:company_id>/departments/', views.department_management, name='department_management'),
    path('company/<int:company_id>/add_department/', views.add_department_for_company, name='add_department_for_company'),
    path('company/<int:company_id>/delete-role/<int:role_id>/', views.delete_role_for_company, name='delete_role_for_company'),
    path('company/<int:company_id>/delete-department/<int:department_id>/', views.delete_department_for_company, name='delete_department_for_company'),
    path('company/<int:company_id>/attendance-dashboard/', views.attendance_dashboard, name='attendance_dashboard'),
    path('company/<int:company_id>/leave-management/',views.leave_requests,name='leave_management'),
    path('manage_leave_request/<int:leave_id>/<str:action>/', views.manage_leave_request, name='manage_leave_request'),
    path('hr/manage-attendance/<int:company_id>/', views.manage_attendance_hr, name='manage_attendance_hr'),
    path('hr/get-employees-by-date/<int:company_id>/', views.get_employees_by_date_hr, name='get_employees_by_date_hr'),
    path("company/<int:company_id>/leave-policies/", views.list_leave_policies, name="list_leave_policies"),
    path("company/<int:company_id>/leave-policies/create/", views.create_leave_policy, name="create_leave_policy"),
    path('leave-policy/delete/<int:policy_id>/<int:company_id>/', views.delete_leave_policy, name='delete_leave_policy'),
    


    
    # Password Reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='users/password_reset_form.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),
    
    
    #manager 
    path('company/<int:company_id>/manager_dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('company/<int:company_id>/manage_attendance/', views.manage_attendance, name='manage_attendance'),
    path('company/<int:company_id>/get_employees_by_date/', views.get_employees_by_date, name='get_employees_by_date'),
    path('company/<int:company_id>/manage_leave_requests/', views.manage_leave_requests, name='manage_leave_requests'),
    path('company/<int:company_id>/tasks/', views.manage_tasks, name='manage_tasks'),
    path('task/delete/<int:task_id>/', views.delete_task, name='delete_task'),
    path('company/<int:company_id>/view-department-employees/', views.view_department_employees, name='view_department_employees'),
    path('company/<int:company_id>/announcements/', views.list_announcements, name='list_announcements'),
    path('company/<int:company_id>/announcements/create/', views.create_announcement, name='create_announcement'),
    path('announcements/<int:announcement_id>/edit/', views.edit_announcement, name='edit_announcement'),
    path('announcements/<int:announcement_id>/delete/', views.delete_announcement, name='delete_announcement'),
    

    #Employee
    path('company/<int:company_id>/view/', views.view_attendance, name='view_attendance'),
    path('company/<int:company_id>/request_correction/<int:attendance_id>/', views.request_correction, name='request_correction'),
    path('approve_correction/<int:attendance_id>/', views.approve_correction, name='approve_correction'),   
    path('company/<int:company_id>/leave/submit/', views.submit_leave_request, name='submit_leave_request'),
    path('company/<int:company_id>/leave/view/', views.view_leave_requests, name='view_leave_requests'),
    path('company/<int:company_id>/leave/update/<int:pk>/', views.update_leave_requests, name='update_leave_request'),
    path('company/<int:company_id>/leave-policy/',views.view_leave_policy_per_company, name='view_leave_policy_per_company'),
    path('company/<int:company_id>/leave-balance/', views.view_leave_balances, name='view_leave_balances'),
    path('company/<int:company_id>/task/', views.view_tasks, name='view_tasks'),
    path('company/<int:company_id>/tasks/update/<int:task_id>/', views.update_task_status, name='update_task_status'),
    path('company/<int:company_id>/announcement/', views.view_announcements, name='view_announcements'),
     



]
