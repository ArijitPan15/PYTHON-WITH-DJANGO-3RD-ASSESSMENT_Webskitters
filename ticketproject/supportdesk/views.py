import json
from typing import Any, Optional, TextIO
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from .forms import TicketForm, PriorityForm


def suggest_priority(severity: str, description: str) -> str:
    word: str

    for word in ['urgent', 'blocked', 'crash', 'data loss']:
        if word in description.lower():
            return 'High'
    return severity.capitalize()


def ticket_form(request: HttpRequest) -> HttpResponse:
    form: TicketForm

    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            data: dict[str, Any] = form.cleaned_data.copy()
            screenshot: Optional[UploadedFile] = data.pop('screenshot')
            saved_path: str = ''

            try:
                if screenshot:
                    saved_path = default_storage.save(
                        'ticket_screenshots/' + screenshot.name, screenshot
                    )

                data['screenshot'] = saved_path
                data['priority'] = suggest_priority(
                    data['severity'], data['description']
                )

                # Append one ticket per line without overwriting old tickets.
                file: TextIO
                with open(settings.BASE_DIR / 'tickets.jsonl', 'a', encoding='utf-8') as file:
                    file.write(json.dumps(data) + '\n')

                return redirect('ticket_success')

            except OSError:
                if saved_path:
                    try:
                        default_storage.delete(saved_path)
                    except OSError:
                        pass

                form.add_error(None, 'Could not save ticket. Please try again.')

    elif request.method == 'GET':
        form = TicketForm()
    else:
        return HttpResponse('Method not allowed', status=405)

    return render(request, 'supportdesk/ticket_form.html', {'form': form})


def ticket_success(request: HttpRequest) -> HttpResponse:
    return render(request, 'supportdesk/ticket_success.html')


def check_priority(request: HttpRequest) -> JsonResponse:
    if request.method == 'POST':
        form: PriorityForm = PriorityForm(request.POST)

        if form.is_valid():
            priority: str = suggest_priority(
                form.cleaned_data['severity'],
                form.cleaned_data['description']
            )

            return JsonResponse({'priority': priority})

        return JsonResponse({'error': 'Enter a valid severity and description.'}, status=400)

    return JsonResponse({'error': 'Only POST is allowed.'}, status=405)