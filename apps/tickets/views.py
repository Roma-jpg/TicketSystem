from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render

from .forms import TicketForm
from .models import Ticket


@login_required
def ticket_create(request):

	if request.method == "POST":

		form = TicketForm(
			request.POST,
			request.FILES,
		)

		if form.is_valid():

			ticket = form.save(commit=False)
			ticket.created_by = request.user
			ticket.save()

			return redirect(
				"tickets:ticket_detail",
				pk=ticket.pk,
			)

	else:
		form = TicketForm()

	return render(
		request,
		"tickets/create.html",
		{
			"form": form
		},
	)


@login_required
def ticket_detail(request, pk):

	ticket = get_object_or_404(
		Ticket,
		pk=pk,
	)

	if (
		request.user != ticket.created_by
		and not request.user.is_it()
	):
		return redirect("home")

	return render(
		request,
		"tickets/detail.html",
		{
			"ticket": ticket
		},
	)