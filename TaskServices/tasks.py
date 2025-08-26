# TaskServices/tasks.py
from TaskServices.models import Task
from cleanswitch.celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def generate_recurring_tasks():
    recurring_tasks = Task.objects.filter(is_recurring=True, active=True)
    
    for task in recurring_tasks:
        if should_generate_task(task):
            create_next_task(task)

def should_generate_task(task):
 # Implement logic to check if a new task should be generated
# based on repeat_interval, repeat_every, repeat_end_date, etc.
    last_child = task.child_tasks.order_by('-due_date').first()
        
    if not last_child:
        return task.due_date <= timezone.now()
            
    if task.repeat_end_date and task.repeat_end_date <= timezone.now():
        return False
            
    next_due_date = calculate_next_due_date(last_child.due_date, task)
    return next_due_date <= timezone.now()

def calculate_next_due_date(self, last_due_date, task):
    if task.repeat_interval == 'daily':
        return last_due_date + timedelta(days=task.repeat_every)
    elif task.repeat_interval == 'weekly':
        return last_due_date + timedelta(weeks=task.repeat_every)
    # Implement other intervals similarly
    return last_due_date

def create_next_task(task):
    last_child = task.child_tasks.order_by('-due_date').first()
    next_due_date = calculate_next_due_date(
            last_child.due_date if last_child else task.due_date,
            task
        )
        
    new_task = Task.objects.create(
        title=task.title,
        description=task.description,
        due_date=next_due_date,
        hours=task.hours,
        property_assigned=task.property_assigned,
        status='pending',
        priority=task.priority,
        active=True,
        is_recurring=True,
        repeat_interval=task.repeat_interval,
        repeat_every=task.repeat_every,
        repeat_end_date=task.repeat_end_date,
        parent_task=task,
        # Copy other fields as needed
        )
    new_task.assigned_to.set(task.assigned_to.all())