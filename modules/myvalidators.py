#!/usr/bin/env python
# coding: utf8
from gluon import *
import re

regex1 = re.compile('\w+\.\w+')
regex2 = re.compile('%\((?P<name>[^\)]+)\)s')

class MAYBE_IN_DB(validators.Validator):
    """
    example::

        INPUT(_type='text', _name='name',
              requires=IS_IN_DB(db, db.mytable.myfield, zero=''))

    used for reference fields, rendered as a dropbox
    """

    def __init__(
        self,
        dbset,
        field,
        label=None,
        error_message='value not in database',
        orderby=None,
        groupby=None,
        distinct=None,
        cache=None,
        optional=False,
        multiple=False,
        zero='',
        sort=False,
        _and=None,
    ):
        from dal import Table
        if isinstance(field, Table):
            field = field._id

        if hasattr(dbset, 'define_table'):
            self.dbset = dbset()
        else:
            self.dbset = dbset
        (ktable, kfield) = str(field).split('.')
        if not label:
            label = '%%(%s)s' % kfield
        if isinstance(label, str):
            if regex1.match(str(label)):
                label = '%%(%s)s' % str(label).split('.')[-1]
            ks = regex2.findall(label)
            if not kfield in ks:
                ks += [kfield]
            fields = ks
        else:
            ks = [kfield]
            fields = 'all'
        self.fields = fields
        self.label = label
        self.ktable = ktable
        self.kfield = kfield
        self.ks = ks
        self.error_message = error_message
        self.theset = None
        self.orderby = orderby
        self.groupby = groupby
        self.distinct = distinct
        self.cache = cache
        self.optional = optional
        self.multiple = multiple
        self.zero = zero
        self.sort = sort
        self._and = _and

    def set_self_id(self, id):
        if self._and:
            self._and.record_id = id

    def build_set(self):
        table = self.dbset.db[self.ktable]
        if self.fields == 'all':
            fields = [f for f in table]
        else:
            fields = [table[k] for k in self.fields]
        if self.dbset.db._dbname != 'gae':
            orderby = self.orderby or reduce(lambda a, b: a | b, fields)
            groupby = self.groupby
            distinct = self.distinct
            dd = dict(orderby=orderby, groupby=groupby,
                      distinct=distinct, cache=self.cache,
                      cacheable=True)
            records = self.dbset(table).select(*fields, **dd)
        else:
            orderby = self.orderby or \
                reduce(lambda a, b: a | b, (
                    f for f in fields if not f.name == 'id'))
            dd = dict(orderby=orderby, cache=self.cache, cacheable=True)
            records = self.dbset(table).select(table.ALL, **dd)
        self.theset = [str(r[self.kfield]) for r in records]
        if isinstance(self.label, str):
            self.labels = [self.label % dict(r) for r in records]
        else:
            self.labels = [self.label(r) for r in records]

    def options(self, zero=True):
        self.build_set()
        items = [(k, self.labels[i]) for (i, k) in enumerate(self.theset)]
        if self.sort:
            items.sort(options_sorter)
        if zero and not self.zero is None and not self.multiple:
            items.insert(0, ('', self.zero))
        return items

    def __call__(self, value):
        table = self.dbset.db[self.ktable]
        field = table[self.kfield]
        if self.optional and (value == None or value == ''):
            return (None, None)
        if self.multiple:
            if self._and:
                raise NotImplementedError
            if isinstance(value, list):
                values = value
            elif value:
                values = [value]
            else:
                values = []
            if isinstance(self.multiple, (tuple, list)) and \
                    not self.multiple[0] <= len(values) < self.multiple[1]:
                return (values, translate(self.error_message))
            if self.theset:
                if not [v for v in values if not v in self.theset]:
                    return (values, None)
            else:
                from dal import GoogleDatastoreAdapter

                def count(values, s=self.dbset, f=field):
                    return s(f.belongs(map(int, values))).count()
                if isinstance(self.dbset.db._adapter, GoogleDatastoreAdapter):
                    range_ids = range(0, len(values), 30)
                    total = sum(count(values[i:i + 30]) for i in range_ids)
                    if total == len(values):
                        return (values, None)
                elif count(values) == len(values):
                    return (values, None)
        elif self.theset:
            if str(value) in self.theset:
                if self._and:
                    return self._and(value)
                else:
                    return (value, None)
        else:
            if self.dbset(field == value).count():
                if self._and:
                    return self._and(value)
                else:
                    return (value, None)
        return (value, translate(self.error_message))
