from pathlib import Path
from django import forms

CATEGORY_CHOICES = [('technical', 'Technical'), ('academic', 'Academic'),
                    ('account', 'Account'), ('other', 'Other')]
SEVERITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]


class TicketForm(forms.Form):
    trainee_name = forms.CharField(max_length=100)
    email = forms.EmailField()
    category = forms.ChoiceField(choices=CATEGORY_CHOICES)
    severity = forms.ChoiceField(choices=SEVERITY_CHOICES)
    description = forms.CharField(min_length=10, max_length=1000, widget=forms.Textarea)
    screenshot = forms.ImageField(required=False)

    def clean_screenshot(self):
        screenshot = self.cleaned_data['screenshot']
        if screenshot:
            extension = Path(screenshot.name).suffix.lower()
            if extension not in ['.png', '.jpg', '.jpeg']:
                raise forms.ValidationError('Only PNG and JPEG files are allowed.')
            if screenshot.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image must be within 5 MB.')
            expected_type = 'PNG' if extension == '.png' else 'JPEG'
            if screenshot.image.format != expected_type:
                raise forms.ValidationError('Image type does not match its extension.')
        return screenshot


class PriorityForm(forms.Form):
    severity = forms.ChoiceField(choices=SEVERITY_CHOICES)
    description = forms.CharField(min_length=10, max_length=1000)
