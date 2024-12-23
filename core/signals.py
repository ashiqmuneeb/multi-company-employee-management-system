from django.db.models.signals import post_delete,post_save
from django.dispatch import receiver
from .models import Company, CustomUser,Role,Department,Employee, LeavePolicy, LeaveBalance

@receiver(post_delete, sender=Company)
def delete_associated_user(sender, instance, **kwargs):
    try:
        # Delete the admin user associated with the company
        if instance.admin_username:
            admin_user = CustomUser.objects.get(username=instance.admin_username)
            admin_user.delete()
    except CustomUser.DoesNotExist:
        # User not found, nothing to delete
        pass

@receiver(post_delete, sender=Employee)
def delete_unused_role_and_department(sender, instance, **kwargs):
    # Check if the department has no other employees
    if instance.department and not instance.department.employees.exists():
        instance.department.delete()

    # Check if the role has no other employees
    if instance.role and not instance.role.employees.exists():
        instance.role.delete()
        

@receiver(post_save, sender=Employee)
def create_leave_balance(sender, instance, created, **kwargs):
    if created:  # Only create leave balances when a new employee is created
        leave_policies = LeavePolicy.objects.filter(company=instance.company)
        for policy in leave_policies:
            LeaveBalance.objects.create(
                employee=instance,
                leave_type=policy,
                remaining_days=policy.max_days_per_year
            )
