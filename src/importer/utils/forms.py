from django import forms


class StaticHiddenField(forms.Field):
    def __init__(self, value, form_value=None):
        self.python_value = value
        self.form_value = value if form_value is None else form_value
        super().__init__(widget=forms.HiddenInput)

    def prepare_value(self, value):
        return self.form_value

    def to_python(self, value):
        return self.python_value
