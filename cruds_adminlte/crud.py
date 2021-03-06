# encoding: utf-8

'''
Free as freedom will be 26/8/2016

@author: luisza
'''


import os
from django.conf.urls import url, include
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseRedirect, HttpResponseForbidden
from django.urls.base import reverse_lazy, reverse
from django.urls.exceptions import NoReverseMatch
from django.views import View
from django.views.generic import (ListView, CreateView, DeleteView,
                                  UpdateView, DetailView)

from cruds_adminlte import utils
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.db.models.query_utils import Q
from django.db import models
from django.shortcuts import get_object_or_404
from cruds_adminlte.filter import get_filters
from collections import OrderedDict
from django.views.generic.edit import ProcessFormView
import types

from betterforms.multiform import MultiModelForm, MultiForm

class CRUDMixin(object):

    def get_template_names(self):
        dev = []
        base_name = "%s/%s/" % (self.model._meta.app_label,
                                self.model.__name__.lower())
        dev.append(base_name + self.template_name)
        dev.append(self.template_name)
        return dev

    def get_search_fields(self, context):
        try:
            context['search'] = self.search_fields
        except AttributeError:
            context['search'] = False
        if self.view_type == 'list' and 'q' in self.request.GET:
            context['q'] = self.request.GET.get('q', '')

    def get_filters(self, context):
        filter_params = []
        if self.view_type == 'list' and self.list_filter:
            filters = get_filters(self.model, self.list_filter, self.request)
            context['filters'] = filters
            for filter in filters:
                param = filter.get_params(self.related_fields or [])
                if param:
                    filter_params += param

        if filter_params:
            if self.getparams:
                self.getparams += "&"
            self.getparams += "&".join(filter_params)

    def validate_user_perms(self, user, perm, view):

        if (hasattr(self, 'get_object') and view == 'update'):
            try:
                obj = self.get_object()
                if (user.has_perm(perm, obj)):
                    return True
            except:
                None
        if isinstance(perm, types.FunctionType):
            return perm(user, view)
        return user.has_perm(perm)

    def get_check_perms(self, context):
        user = self.request.user
        available_perms = {}
        for perm in self.all_perms:
            if self.check_perms:
                if perm in self.views_available:
                    available_perms[perm] = all([
                        self.validate_user_perms(user, x, perm)
                        for x in self.all_perms[perm]])
                else:
                    available_perms[perm] = False
            else:
                available_perms[perm] = True
        context['crud_perms'] = available_perms

    def get_urls_and_fields(self, context):
        include = None
        if hasattr(self, 'display_fields') and self.view_type == 'detail':
            include = getattr(self, 'display_fields')

        if hasattr(self, 'list_fields') and self.view_type == 'list':
            include = getattr(self, 'list_fields')

        context['fields'] = utils.get_fields(self.model, include=include)
        if hasattr(self, 'object') and self.object:
            for action in utils.INSTANCE_ACTIONS:
                try:
                    nurl = utils.crud_url_name(self.model, action)
                    if self.namespace:
                        nurl = self.namespace + ':' + nurl
                    url = reverse(nurl, kwargs={'pk': self.object.pk})
                except NoReverseMatch:
                    url = None
                context['url_%s' % action] = url

        for action in utils.LIST_ACTIONS:
            try:
                nurl = utils.crud_url_name(self.model, action)
                if self.namespace:
                    nurl = self.namespace + ':' + nurl
                url = reverse(nurl)
            except NoReverseMatch:
                url = None
            context['url_%s' % action] = url

    def get_context_data(self, **kwargs):
        """
        Adds available urls and names.
        """
        context = super(CRUDMixin, self).get_context_data(**kwargs)
        context.update({
            'model_verbose_name': self.model._meta.verbose_name,
            'model_verbose_name_plural': self.model._meta.verbose_name_plural,
            'namespace': self.namespace
        })
        context.update({'blocks': self.template_blocks})

        if self.view_type in ['update', 'detail']:
            context['inlines'] = self.inlines

        if 'object' not in context:
            context['object'] = self.model

        self.get_urls_and_fields(context)
        self.get_check_perms(context)
        self.get_search_fields(context)
        self.get_filters(context)

        context['views_available'] = self.views_available
        if self.view_type == 'list':
            context['paginate_template'] = self.paginate_template
            context['paginate_position'] = self.paginate_position

        context['template_father'] = self.template_father

        context.update(self.context_rel)
        context['getparams'] = "?" + self.getparams
        context['getparams'] += "&" if self.getparams else ""
        return context

    def dispatch(self, request, *args, **kwargs):
        self.related_fields = self.related_fields or []
        self.context_rel = {}
        getparams = []
        self.getparams = ''

        #TODO: fix search in related tables
        for related in self.related_fields:
            #TODO: pk = request.GET something like model name??
            pk = self.request.GET.get(related, '')
            if pk:
                Classrelated = utils.get_related_class_field(
                    self.model, related)
                self.context_rel[related] = get_object_or_404(
                    Classrelated, pk=pk)
                getparams.append("%s=%s" % (
                    related, str(self.context_rel[related].pk)))

        if getparams:
            self.getparams = "&".join(getparams)
        for perm in self.perms:
            if not self.validate_user_perms(request.user, perm,
                                            self.view_type):
                return HttpResponseForbidden()
        return View.dispatch(self, request, *args, **kwargs)


class CRUDView(object):
    """
        CRUDView is a generic way to provide create, list, detail, update,
        delete views in one class,
        you can inherit for it and manage login_required, model perms,
        pagination, update and add forms
        how to use:

        In views

        .. code:: python

            from testapp.models import Customer
            from cruds_adminlte.crud import CRUDView
            class Myclass(CRUDView):
                model = Customer

        In urls.py

        .. code:: python
            myview = Myclass()
            urlpatterns = [
                url('path', include(myview.get_urls()))  # also support
                                                         # namespace
            ]

        The default behavior is check_login = True and check_perms=True but
        you can turn off with

        .. code:: python
            from testapp.models import Customer
            from cruds_adminlte.crud import CRUDView

            class Myclass(CRUDView):
                model = Customer
                check_login = False
                check_perms = False

        You also can defined extra perms with

        .. code:: python

            class Myclass(CRUDView):
                model = Customer
                perms = { 'create': ['applabel.mycustom_perm'],
                          'list': [],
                          'delete': [],
                          'update': [],
                          'detail': []
                        }
        If check_perms = True we will add default django model perms
         (<applabel>.[add|change|delete|view]_<model>)

        You can also overwrite add and update forms

        .. code:: python

            class Myclass(CRUDView):
                model = Customer
                add_form = MyFormClass
                update_form = MyFormClass

        And of course overwrite base template name

        .. code:: python

            class Myclass(CRUDView):
                model = Customer
                template_name_base = "mybase"

        Remember basename is generated like app_label/modelname if
        template_name_base is set as None and
        'cruds' by default so template loader search this structure

        basename + '/create.html'
        basename + '/detail.html'
        basename + '/update.html'
        basename + '/list.html'
        basename + '/delete.html'
        Note: also import <applabel>/<model>/<basename>/<view type>.html

        Using namespace

        In views

        .. code:: python

            from testapp.models import Customer
            from cruds_adminlte.crud import CRUDView
            class Myclass(CRUDView):
                model = Customer
                namespace = "mynamespace"

        In urls.py

        .. code:: python

            myview = Myclass()
            urlpatterns = [
                url('path', include(myview.get_urls(),
                                    namespace="mynamespace"))
            ]

        If you want to filter views add views_available list

        .. code:: python
            class Myclass(CRUDView):
                model = Customer
                views_available = ['create', 'list', 'delete',
                                   'update', 'detail']

    """

    model = None
    template_name_base = "cruds"
    template_blocks = {}
    namespace = None
    fields = '__all__'
    urlprefix = ""
    check_login = True
    check_perms = True
    paginate_by = 10
    paginate_template = 'cruds/pagination/prev_next.html'
    paginate_position = 'Bottom'
    update_form = None
    add_form = None
    display_fields = None
    list_fields = None
    inlines = None
    views_available = None
    template_father = "cruds/base.html"
    search_fields = None
    split_space_search = False
    related_fields = None
    list_filter = None

    """
    It's obligatory this structure
        perms = {
        'create': [],
        'list': [],
        'delete': [],
        'update': [],
        'detail': []
        }
    """
    perms = None

    #  DECORATORS

    def check_decorator(self, viewclass):
        if self.check_login:
            return login_required(viewclass)
        return viewclass

    def decorator_create(self, viewclass):
        return self.check_decorator(viewclass)

    def decorator_detail(self, viewclass):
        return self.check_decorator(viewclass)

    def decorator_list(self, viewclass):
        return self.check_decorator(viewclass)

    def decorator_update(self, viewclass):
        return self.check_decorator(viewclass)

    def decorator_delete(self, viewclass):
        return self.check_decorator(viewclass)

    #  GET GENERIC CLASS

    def get_create_view_class(self):
        return CreateView

    def get_create_view(self):
        CreateViewClass = self.get_create_view_class()

        class OCreateView(CRUDMixin, CreateViewClass):
            namespace = self.namespace
            perms = self.perms['create']
            all_perms = self.perms
            form_class = self.add_form
            view_type = 'create'
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            related_fields = self.related_fields
            multiForm = None
            self.object = None

            def get(self, request, *args, **kwargs):
                self.multiForm = self.form_class()
                return super(OCreateView, self).get(request, *args, **kwargs)

            def post(self, request, *args, **kwargs):
                self.multiForm = self.form_class(data=request.POST)
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    if self.multiForm.is_valid():
                        self.object = self.multiForm.save(commit=True)
                        return HttpResponseRedirect(self.get_success_url())
                    else:
                        self.object = None
                        self.multiForm.request = request
                        self.form = self.multiForm
                        return super(OCreateView, self).post(request, *args, **kwargs)
                else:
                    return super(OCreateView, self).post(request, *args, **kwargs)

            def get_form(self):
                return self.multiForm

            def form_valid(self, form):
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    return self.multiForm.is_valid()
                else:
                    if not self.related_fields:
                        return super(OCreateView, self).form_valid(form)

                    self.object = form.save(commit=False)
                    for key, value in self.context_rel.items():
                        setattr(self.object, key, value)
                    self.object.save()
                    return HttpResponseRedirect(self.get_success_url())

            def get_success_url(self):
                url = super(OCreateView, self).get_success_url()
                if (self.getparams):  # fixed filter create action
                    url += '?' + self.getparams
                return url

        return OCreateView

    def get_detail_view_class(self):
        return DetailView

    def get_detail_view(self):
        ODetailViewClass = self.get_detail_view_class()

        class ODetailView(CRUDMixin, ODetailViewClass):
            namespace = self.namespace
            perms = self.perms['detail']
            all_perms = self.perms
            view_type = 'detail'
            display_fields = self.display_fields
            inlines = self.inlines
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            related_fields = self.related_fields

            def get_success_url(self):
                url = super(ODetailView, self).get_success_url()
                if (self.getparams):  # fixed filter detail action
                    url += '?' + self.getparams
                return url

        return ODetailView

    def get_update_view_class(self):
        return UpdateView

    def get_update_view(self):
        EditViewClass = self.get_update_view_class()

        class OEditView(CRUDMixin, EditViewClass):
            namespace = self.namespace
            perms = self.perms['update']
            form_class = self.update_form
            all_perms = self.perms
            view_type = 'update'
            inlines = self.inlines
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            related_fields = self.related_fields
            multiForm = None
            proxyFields = {}

            def get(self, request, pk, *args, **kwargs):
                self.multiForm = self.form_class()

                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    self.objects = self.multiForm.get_objects(pk)
                    self.multiForm.set_objects(pk)
                    #self.object = next(iter(self.objects.items()))[1]
                    self.object = self.multiForm.get_proxy_model(self.objects)
                    self.model = self.object.__class__
                    self.multiForm = self.form_class(instance=self.objects)
                    self.form_class = self.form_class(instance=self.objects)

                return super(OEditView, self).get(request, *args, **kwargs)

            def get_form(self):
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    return self.multiForm
                else:
                    return super(OEditView, self).get_form()

            def get_object(self):
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    return self.object
                else:
                    return super(OEditView, self).get_object()

            def get_urls_and_fields(self, context):
                include = None
                if hasattr(self, 'display_fields') and self.view_type == 'detail':
                    include = getattr(self, 'display_fields')

                if hasattr(self, 'list_fields') and self.view_type == 'list':
                    include = getattr(self, 'list_fields')

                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    for fieldName in self.multiForm.requestData.keys():
                        cls, objField = self.multiForm.requestData[fieldName]
                        objField.html_name = '%s' % (fieldName)
                        self.proxyFields[fieldName] = ( fieldName, objField )
                    context['fields'] = OrderedDict([ (x, self.proxyFields[x]) for x in self.proxyFields ])
                else:
                    context['fields'] = utils.get_fields(self.model, include=include)

                if hasattr(self, 'object') and self.object:
                    for action in utils.INSTANCE_ACTIONS:
                        try:
                            nurl = utils.crud_url_name(self.model, action)
                            if self.namespace:
                                nurl = self.namespace + ':' + nurl
                            url = reverse(nurl, kwargs={'pk': self.object.pk})
                        except NoReverseMatch:
                            url = None
                        context['url_%s' % action] = url

                for action in utils.LIST_ACTIONS:
                    try:
                        nurl = utils.crud_url_name(self.model, action)
                        if self.namespace:
                            nurl = self.namespace + ':' + nurl
                        url = reverse(nurl)
                    except NoReverseMatch:
                        url = None
                    context['url_%s' % action] = url

                context['url_list'] = str(os.sep).join([ x for x in self.request.path.split(os.sep) if not utils.is_number(x) ]).replace('update', 'list')
                context['url_detail'] = self.request.path.replace('update', 'detail')
                context['url_update'] = self.request.path
                context['url_delete'] = self.request.path.replace('update', 'delete')
 
            def post(self, request, pk, *args, **kwargs):
                self.tmpForm = self.form_class(data=request.POST)
                if (isinstance(self.tmpForm, MultiModelForm) or isinstance(self.tmpForm, MultiForm)):
                    self.tmpForm.set_objects(pk, data=request.POST)
                    if self.tmpForm.is_valid():
                        self.object = self.tmpForm.save(commit=True)
                        return HttpResponseRedirect(self.get_success_url())
                    else:
                        #self.object = self.tmpForm.save(commit=False)
                        self.form = self.tmpForm
                        self.tmpForm.request = request
                        return super(OEditView, self).post(request, *args, **kwargs)
                else:
                    return super(OEditView, self).post(request, *args, **kwargs)

            def form_valid(self, form):
                if not self.related_fields:
                    return super(OEditView, self).form_valid(form)

                self.object = form.save(commit=False)
                for key, value in self.context_rel.items():
                    setattr(self.object, key, value)
                self.object.save()
                return HttpResponseRedirect(self.get_success_url())

            def get_success_url(self):
                url = super(OEditView, self).get_success_url()
                if (self.getparams):  # fixed filter edit action
                    url += '?' + self.getparams
                return url

        return OEditView

    def get_list_view_class(self):
        return ListView

    def get_list_view(self):
        OListViewClass = self.get_list_view_class()

        class OListView(CRUDMixin, OListViewClass):
            namespace = self.namespace
            perms = self.perms['list']
            all_perms = self.perms
            list_fields = self.list_fields
            view_type = 'list'
            paginate_by = self.paginate_by
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            search_fields = self.search_fields
            split_space_search = self.split_space_search
            related_fields = self.related_fields
            paginate_template = self.paginate_template
            paginate_position = self.paginate_position
            list_filter = self.list_filter

            def get_listfilter_queryset(self, queryset):
                if self.list_filter:
                    filters = get_filters(
                        self.model, self.list_filter, self.request)
                    for filter in filters:
                        queryset = filter.get_filter(queryset)

                return queryset

            def search_queryset(self, query):
                if self.split_space_search is True:
                    self.split_space_search = ' '

                if self.search_fields and 'q' in self.request.GET:
                    q = self.request.GET.get('q')
                    if self.split_space_search:
                        q = q.split(self.split_space_search)
                    elif q:
                        q = [q]
                    sfilter = None
                    for field in self.search_fields:
                        for qsearch in q:
                            if field not in self.context_rel:
                                if sfilter is None:
                                    sfilter = Q(**{field: qsearch})
                                else:
                                    sfilter |= Q(**{field: qsearch})
                    if sfilter is not None:
                        query = query.filter(sfilter)

                if self.related_fields:
                    query = query.filter(**self.context_rel)
                return query

            def get_success_url(self):
                url = super(OListView, self).get_success_url()
                if (self.getparams):  # fixed filter detail action
                    url += '?' + self.getparams
                return url

            def get_queryset(self):
                queryset = super(OListView, self).get_queryset()
                queryset = self.search_queryset(queryset)
                queryset = self.get_listfilter_queryset(queryset)
                return queryset

        return OListView

    def get_delete_view_class(self):
        return DeleteView

    def get_delete_view(self):
        ODeleteClass = self.get_delete_view_class()

        class ODeleteView(CRUDMixin, ODeleteClass):
            namespace = self.namespace
            perms = self.perms['delete']
            all_perms = self.perms
            view_type = 'delete'
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            related_fields = self.related_fields

            def get_success_url(self):
                url = super(ODeleteView, self).get_success_url()
                print(self.getparams)
                if (self.getparams):  # fixed filter delete action
                    url += '?' + self.getparams
                return url

        return ODeleteView

#  INITIALIZERS
    def initialize_create(self, basename):
        OCreateView = self.get_create_view()
        url = utils.crud_url_name(
            self.model, 'list', prefix=self.urlprefix)
        if self.namespace:
            url = self.namespace + ":" + url

        fields = self.fields
        if self.add_form:
            fields = None
        self.create = self.decorator_create(OCreateView.as_view(
            model=self.model,
            fields=fields,
            success_url=reverse_lazy(url),
            template_name=basename
        ))

    def initialize_detail(self, basename):
        ODetailView = self.get_detail_view()
        self.detail = self.decorator_detail(
            ODetailView.as_view(
                model=self.model,
                template_name=basename
            ))

    def initialize_update(self, basename):
        OUpdateView = self.get_update_view()
        url = utils.crud_url_name(
            self.model, 'list', prefix=self.urlprefix)
        if self.namespace:
            url = self.namespace + ":" + url
        fields = self.fields
        if self.update_form:
            fields = None

        if (isinstance(self.update_form, MultiModelForm) or isinstance(self.update_form, MultiForm)):
            self.model = self.update_form.object
            fields = OrderedDict([ (x, self.update_form.proxyFields[x]) for x in self.update_form.proxyFields ])

        self.update = self.decorator_update(OUpdateView.as_view(
            model=self.model,
            fields=fields,
            success_url=reverse_lazy(url),
            template_name=basename
        ))

    def initialize_list(self, basename):
        OListView = self.get_list_view()
        self.list = self.decorator_list(OListView.as_view(
            model=self.model,
            template_name=basename
        ))

    def initialize_delete(self, basename):
        ODeleteView = self.get_delete_view()
        url = utils.crud_url_name(
            self.model, 'list', prefix=self.urlprefix)
        if self.namespace:
            url = self.namespace + ":" + url
        self.delete = self.decorator_delete(ODeleteView.as_view(
            model=self.model,
            success_url=reverse_lazy(url),
            template_name=basename
        ))

    def get_base_name(self):
        ns = self.template_name_base
        if not self.template_name_base:
            ns = "%s/%s" % (
                self.model._meta.app_label,
                self.model.__name__.lower())
        return ns

    def check_create_perm(self, applabel, name):
        notfollow = False
        try:
            model, created = ContentType.objects.get_or_create(
                app_label=applabel, model=name)
        except:
            notfollow = True
        if not notfollow and not Permission.objects.filter(content_type=model,
                                                           codename="view_%s" %
                                                           (name, )).exists():
            Permission.objects.create(
                content_type=model,
                codename="view_%s" % (name,),
                name=_("Can see available %s" % (name,)))

    def initialize_perms(self):
        if self.perms is None:
            self.perms = {
                'create': [],
                'list': [],
                'delete': [],
                'update': [],
                'detail': []

            }
        applabel = self.model._meta.app_label
        name = self.model.__name__.lower()
        if self.check_perms:
            self.check_create_perm(applabel, name)
            self.perms['create'].append("%s.add_%s" % (applabel, name))
            self.perms['update'].append("%s.change_%s" % (applabel, name))
            self.perms['delete'].append("%s.delete_%s" % (applabel, name))
            # maybe other default perm can be here
            self.perms['list'].append("%s.view_%s" % (applabel, name))
            self.perms['detail'].append("%s.view_%s" % (applabel, name))

    def inicialize_views_available(self):
        if self.views_available is None:
            self.views_available = [
                'create', 'list', 'delete', 'update', 'detail']

    def __init__(self, namespace=None, model=None, template_name_base=None):
        if namespace:
            self.namespace = namespace
        if model:
            self.model = model
        if template_name_base:
            self.template_name_base = template_name_base

        basename = self.get_base_name()
        self.inicialize_views_available()
        self.initialize_perms()
        if 'create' in self.views_available:
            self.initialize_create(basename + '/create.html')

        if 'detail' in self.views_available:
            self.initialize_detail(basename + '/detail.html')

        if 'update' in self.views_available:
            self.initialize_update(basename + '/update.html')

        if 'list' in self.views_available:
            self.initialize_list(basename + '/list.html')

        if 'delete' in self.views_available:
            self.initialize_delete(basename + '/delete.html')

    def get_urls(self):

        pre = ""
        try:
            if self.cruds_url:
                pre = "%s/" % self.cruds_url
        except AttributeError:
            pre = ""
        base_name = "%s%s/%s" % (pre, self.model._meta.app_label,
                                 self.model.__name__.lower())
        myurls = []
        if 'list' in self.views_available:
            myurls.append(url("^%s/list$" % (base_name,),
                              self.list,
                              name=utils.crud_url_name(
                                  self.model, 'list', prefix=self.urlprefix)))
        if 'create' in self.views_available:
            myurls.append(url("^%s/create$" % (base_name,),
                              self.create,
                              name=utils.crud_url_name(
                                  self.model, 'create', prefix=self.urlprefix))
                          )
        if 'detail' in self.views_available:
            myurls.append(url('^%s/(?P<pk>[^/]+)$' % (base_name,),
                              self.detail,
                              name=utils.crud_url_name(
                                  self.model, 'detail', prefix=self.urlprefix))
                          )
        if 'update' in self.views_available:
            myurls.append(url("^%s/(?P<pk>[^/]+)/update$" % (base_name,),
                              self.update,
                              name=utils.crud_url_name(
                                  self.model, 'update', prefix=self.urlprefix))
                          )
        if 'delete' in self.views_available:
            myurls.append(url(r"^%s/(?P<pk>[^/]+)/delete$" % (base_name,),
                              self.delete,
                              name=utils.crud_url_name(
                                  self.model, 'delete', prefix=self.urlprefix))
                          )

        myurls += self.add_inlines(base_name)
        return myurls

    def add_inlines(self, base_name):
        dev = []
        if self.inlines:
            for i, inline in enumerate(self.inlines):
                klass = inline()
                self.inlines[i] = klass
                if self.namespace:
                    dev.append(
                        url('^inline/',
                            include(klass.get_urls(),
                                    namespace=self.namespace))
                    )
                else:
                    dev.append(
                        url('^inline/', include(klass.get_urls()))

                    )
        return dev


class UserCRUDView(CRUDView):

    def get_create_view(self):
        View = super(UserCRUDView, self).get_create_view()
        class UCreateView(View):

            def form_valid(self, form):
                self.object = form.save(commit=False)
                self.object.user = self.request.user
                self.object.save()
                return HttpResponseRedirect(self.get_success_url())
        return UCreateView

    def get_update_view(self):
        View = super(UserCRUDView, self).get_update_view()

        class UUpdateView(View):

            def form_valid(self, form):
                self.object = form.save(commit=False)
                self.object.user = self.request.user
                self.object.save()
                return HttpResponseRedirect(self.get_success_url())
        return UUpdateView

    def get_list_view(self):
        View = super(UserCRUDView, self).get_list_view()

        class UListView(View):

            def get_queryset(self):
                queryset = super(UListView, self).get_queryset()
                queryset = queryset.filter(user=self.request.user)
                return queryset
        return UListView

class JSONView(CRUDView, object):
    """
        JSONView extends CRUDView to provide a JSON representation of the form

        It converts the html views into json using the extra templates, only for create and update views
        basename + '/create_json.html'
        basename + '/update_json.html'
        Note: also import <applabel>/<model>/<basename>/<view type>.html
    """
    def __init__(self, namespace=None, model=None, template_name_base=None):
        if namespace:
            self.namespace = namespace
        if model:
            self.model = model
        if template_name_base:
            self.template_name_base = template_name_base

        basename = self.get_base_name()
        self.inicialize_views_available()
        self.initialize_perms()
        if 'create' in self.views_available:
            self.initialize_create(basename + '/create_json.html')

        if 'update' in self.views_available:
            self.initialize_update(basename + '/update_json.html')

    def get_urls(self):

        pre = ""
        try:
            if self.cruds_url:
                pre = "%s/" % self.cruds_url
        except AttributeError:
            pre = ""
        base_name = "%s%s/%s" % (pre, self.model._meta.app_label,
                                 self.model.__name__.lower())
        myurls = []
        if 'create' in self.views_available:
            myurls.append(url("^%s_json/create$" % (base_name,),
                              self.create,
                              name=utils.crud_url_name(
                                  self.model, 'create', prefix=self.urlprefix))
                          )
        if 'update' in self.views_available:
            myurls.append(url("^%s_json/(?P<pk>[^/]+)/update$" % (base_name,),
                              self.update,
                              name=utils.crud_url_name(
                                  self.model, 'update', prefix=self.urlprefix))
                          )
        myurls += self.add_inlines(base_name)
        return myurls

    def get_create_view(self):
        CreateViewClass = self.get_create_view_class()

        class OCreateView(CRUDMixin, CreateViewClass):
            namespace = self.namespace
            perms = self.perms['create']
            all_perms = self.perms
            form_class = self.add_form
            view_type = 'create'
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            related_fields = self.related_fields
            multiForm = None

            def get(self, request, *args, **kwargs):
                self.object = None
                self.multiForm = self.form_class()
                self.get_context_data()
                return super(OCreateView, self).get(request, *args, **kwargs)

            def post(self, request, *args, **kwargs):
                self.object = None
                self.multiForm = self.form_class(data=request.POST)
                self.get_context_data()
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    if self.multiForm.is_valid():
                        self.object = self.multiForm.save(commit=True)
                        return HttpResponseRedirect(self.get_success_url())
                    else:
                        self.object = None
                        self.multiForm.request = request
                        self.form = self.multiForm
                        return super(OCreateView, self).post(request, *args, **kwargs)
                else:
                    return super(OCreateView, self).post(request, *args, **kwargs)

            def get_form(self):
                return self.multiForm

            def form_valid(self, form):
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    return self.multiForm.is_valid()
                else:
                    if not self.related_fields:
                        return super(OCreateView, self).form_valid(form)

                    self.object = form.save(commit=False)
                    for key, value in self.context_rel.items():
                        setattr(self.object, key, value)
                    self.object.save()
                    return HttpResponseRedirect(self.get_success_url())

            def get_success_url(self):
                url = super(OCreateView, self).get_success_url()
                if (self.getparams):  # fixed filter create action
                    url += '?' + self.getparams
                return url

        return OCreateView


    def get_update_view(self):
        EditViewClass = self.get_update_view_class()

        class OEditView(CRUDMixin, EditViewClass):
            namespace = self.namespace
            perms = self.perms['update']
            form_class = self.update_form
            all_perms = self.perms
            view_type = 'update'
            inlines = self.inlines
            views_available = self.views_available[:]
            check_perms = self.check_perms
            template_father = self.template_father
            template_blocks = self.template_blocks
            related_fields = self.related_fields
            multiForm = None
            proxyFields = {}
            self.object = None

            def get(self, request, pk, *args, **kwargs):
                self.multiForm = self.form_class()
                self.get_context_data()

                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    self.objects = self.multiForm.get_objects(pk)
                    self.multiForm.set_objects(pk)
                    #self.object = next(iter(self.objects.items()))[1]
                    self.object = self.multiForm.get_proxy_model(self.objects)
                    self.model = self.object.__class__
                    self.multiForm = self.form_class(instance=self.objects)
                    self.form_class = self.form_class(instance=self.objects)

                return super(OEditView, self).get(request, *args, **kwargs)

            def get_form(self):
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    return self.multiForm
                else:
                    return super(OEditView, self).get_form()

            def get_object(self):
                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    return self.object
                else:
                    return super(OEditView, self).get_object()

            def get_urls_and_fields(self, context):
                include = None
                if hasattr(self, 'display_fields') and self.view_type == 'detail':
                    include = getattr(self, 'display_fields')

                if hasattr(self, 'list_fields') and self.view_type == 'list':
                    include = getattr(self, 'list_fields')

                if (isinstance(self.multiForm, MultiModelForm) or isinstance(self.multiForm, MultiForm)):
                    for fieldName in self.multiForm.requestData.keys():
                        cls, objField = self.multiForm.requestData[fieldName]
                        objField.html_name = '%s' % (fieldName)
                        self.proxyFields[fieldName] = ( fieldName, objField )
                    context['fields'] = OrderedDict([ (x, self.proxyFields[x]) for x in self.proxyFields ])
                else:
                    context['fields'] = utils.get_fields(self.model, include=include)

                if hasattr(self, 'object') and self.object:
                    for action in utils.INSTANCE_ACTIONS:
                        try:
                            nurl = utils.crud_url_name(self.model, action)
                            if self.namespace:
                                nurl = self.namespace + ':' + nurl
                            url = reverse(nurl, kwargs={'pk': self.object.pk})
                        except NoReverseMatch:
                            url = None
                        context['url_%s' % action] = url

                for action in utils.LIST_ACTIONS:
                    try:
                        nurl = utils.crud_url_name(self.model, action)
                        if self.namespace:
                            nurl = self.namespace + ':' + nurl
                        url = reverse(nurl)
                    except NoReverseMatch:
                        url = None
                    context['url_%s' % action] = url

                context['url_list'] = str(os.sep).join([ x for x in self.request.path.split(os.sep) if not utils.is_number(x) ]).replace('update', 'list')
                context['url_detail'] = self.request.path.replace('update', 'detail')
                context['url_update'] = self.request.path
                context['url_delete'] = self.request.path.replace('update', 'delete')

            def post(self, request, pk, *args, **kwargs):
                self.tmpForm = self.form_class(data=request.POST)
                self.get_context_data()
                if (isinstance(self.tmpForm, MultiModelForm) or isinstance(self.tmpForm, MultiForm)):
                    self.tmpForm.set_objects(pk, data=request.POST)
                    if self.tmpForm.is_valid():
                        self.object = self.tmpForm.save(commit=True)
                        return HttpResponseRedirect(self.get_success_url())
                    else:
                        #self.object = self.tmpForm.save(commit=False)
                        self.form = self.tmpForm
                        self.tmpForm.request = request
                        return super(OEditView, self).post(request, *args, **kwargs)
                else:
                    return super(OEditView, self).post(request, *args, **kwargs)

            def form_valid(self, form):
                if not self.related_fields:
                    return super(OEditView, self).form_valid(form)

                self.object = form.save(commit=False)
                for key, value in self.context_rel.items():
                    setattr(self.object, key, value)
                self.object.save()
                return HttpResponseRedirect(self.get_success_url())

            def get_success_url(self):
                url = super(OEditView, self).get_success_url()
                if (self.getparams):  # fixed filter edit action
                    url += '?' + self.getparams
                return url

        return OEditView
