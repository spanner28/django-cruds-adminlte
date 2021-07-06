from django.forms.utils import flatatt
from django.forms.widgets import Widget, Textarea
from django.template import loader
from django.utils.safestring import mark_safe
from django.conf import settings

class ImageWidget(Widget):

    template_name = 'widgets/image.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class DatePickerWidget(Widget):

    template_name = 'widgets/datepicker.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        if 'format' not in context:
            context['format'] = 'mm/dd/yyyy'
        context['djformat'] = settings.DATE_FORMAT
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class TimePickerWidget(Widget):

    template_name = 'widgets/timepicker.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        if 'format' not in context:
            context['format'] = 'HH:ii P'
        context['djformat'] = settings.TIME_FORMAT
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class DateTimePickerWidget(Widget):

    template_name = 'widgets/datetimepicker.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value

        if 'format' not in context:
            context['format'] = 'mm/dd/yyyy hh:ii:ss'
        context['djformat'] = settings.DATETIME_FORMAT

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class ColorPickerWidget(Widget):

    template_name = 'widgets/colorpicker.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))


class CKEditorWidget(Textarea):

    template_name = 'widgets/ckeditor.html'

    def get_context(self, name, value, attrs=None):
        self.attrs['flatatt'] = flatatt(self.attrs)
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

class SelectManyWidget(Widget):

    template_name = 'widgets/selectmany.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)
        context['name'] = name
        if value is not None:
            context['value'] = value
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

class ListAddOneWidget(Widget):

    template_name = 'widgets/listaddone.html'

    def get_context(self, name, value, attrs=None):
        context = dict(self.attrs.items())
        if attrs is not None:
            context.update(attrs)

        context['name'] = name
        if value is not None:
            context['value'] = value
            if 'model' in context and 'list_fields' in context:
                context['items'] = self.list_display(context['model'], value, context['list_fields'])
                context['model_name'] = context['model'].__name__

        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        return mark_safe(loader.render_to_string(self.template_name, context))

    def list_model(self, model, ids = []):
        manager = getattr(model, 'objects')
        return manager.filter(**{'%s__in' % model()._meta.pk.name: ids}).all()

    def list_display(self, model, ids, list_fields = []):
        items = self.list_model(model, ids)
        resItems = []
        for item in items:
            obj = {}
            for lf in list_fields:
                if len(lf.split('__')) > 1:
                    # find related field
                    # todo: support recursive __
                    fieldParts = lf.split('__')
                    relatedObject = getattr(item, fieldParts[0])
                    obj[lf] = getattr(relatedObject, fieldParts[1])
                else:
                    obj[lf] = getattr(item, lf)

            resItems.append(obj)
        return resItems
