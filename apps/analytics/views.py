# apps/analytics/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Avg, F, Q
from apps.tickets.models import Ticket
from django.db.models import Case, When, Value, CharField

@login_required
def dashboard(request):
    if not request.user.is_it() and not request.user.is_principal() and not request.user.is_staff:
        return render(request, "403.html", status=403)

    now = timezone.now()
    today = now.date()
    last_7_days = today - timezone.timedelta(days=6)

    open_count = Ticket.objects.filter(status__in=['open', 'reopened', 'acknowledged']).count()
    in_progress_count = Ticket.objects.filter(status='in_progress').count()
    overdue_count = Ticket.objects.filter(is_overdue=True).count()
    resolved_today = Ticket.objects.filter(
        resolved_at__date=today
    ).count()

    avg_resolution = Ticket.objects.filter(
        resolved_at__isnull=False,
        resolved_at__gte=now - timezone.timedelta(days=30)
    ).aggregate(
        avg_hours=Avg(F('resolved_at') - F('created_at'))
    )['avg_hours']
    if avg_resolution:
        avg_hours = avg_resolution.total_seconds() / 3600
    else:
        avg_hours = None

    status_counts = Ticket.objects.values('status').annotate(count=Count('status')).order_by('status')

    daily_created = []
    for i in range(7):
        day = today - timezone.timedelta(days=i)
        count = Ticket.objects.filter(created_at__date=day).count()
        daily_created.append({
            'date': day.strftime('%d.%m'),
            'count': count
        })
    daily_created.reverse()

    busy_rooms = Ticket.objects.values('room_number').annotate(
        total=Count('id')
    ).order_by('-total')[:5]

    # New statistics
    device_stats = Ticket.objects.values('device_type').annotate(
        count=Count('id'),
        display_name=Case(
            *[When(device_type=val, then=Value(label)) for val, label in Ticket.DeviceTypes.choices],
            output_field=CharField()
        )
    ).order_by('-count')

    teacher_stats = Ticket.objects.filter(created_by__role='teacher').values(
        'created_by__username'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    context = {
        'open_count': open_count,
        'in_progress_count': in_progress_count,
        'overdue_count': overdue_count,
        'resolved_today': resolved_today,
        'avg_hours': avg_hours,
        'status_counts': list(status_counts),
        'daily_created': daily_created,
        'busy_rooms': busy_rooms,
        'device_stats': device_stats,
        'teacher_stats': teacher_stats,
    }
    return render(request, 'analytics/dashboard.html', context)