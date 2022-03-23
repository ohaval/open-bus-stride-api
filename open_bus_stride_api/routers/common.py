import typing

import fastapi
import pydantic
import sqlalchemy

from open_bus_stride_db.db import get_session


def get_list(*args, convert_to_dict=None, **kwargs):
    with get_session() as session:
        if convert_to_dict is None:
            return [obj.__dict__ for obj in get_list_query(session, *args, **kwargs)]
        else:
            return [convert_to_dict(obj) for obj in get_list_query(session, *args, **kwargs)]


def get_list_query(session, db_model, limit, offset, filters=None, max_limit=100,
                   order_by=None, allowed_order_by_fields=None,
                   post_session_query_hook=None):
    if not limit and max_limit:
        limit = max_limit
    assert limit <= max_limit, f'max allowed limit is {max_limit}'
    if filters is None:
        filters = []
    session_query = session.query(db_model)
    if post_session_query_hook:
        session_query = post_session_query_hook(session_query)
    for filter in filters:
        session_query = globals()['get_list_query_filter_{}'.format(filter['type'])](session_query, filters, filter)
    if order_by:
        order_by_args = []
        for ob in order_by.split(','):
            ob = ob.strip()
            if not ob:
                continue
            ob = ob.split()
            if len(ob) == 1:
                field_name = ob[0]
                direction = None
            else:
                field_name, direction = ob
            assert not allowed_order_by_fields or field_name in allowed_order_by_fields, 'field name is not in allowed order_by fields: {}'.format(field_name)
            order_by_args.append((sqlalchemy.desc if direction == 'desc' else sqlalchemy.asc)(getattr(db_model, field_name)))
        session_query = session_query.order_by(*order_by_args)
    if limit:
        session_query = session_query.limit(limit)
    if offset:
        session_query = session_query.offset(offset)
    return session_query


def get_list_query_filter_equals(session_query, filters, filter):
    if filter['value'] is not None:
        session_query = session_query.filter(filter['field'] == filter['value'])
    return session_query


def get_list_query_filter_in(session_query, filters, filter):
    value = filter['value']
    if value is not None:
        if isinstance(value, str):
            value = value.split(',')
        if len(value) > 0:
            assert len(value) <= 1000, 'too many items in list, maximum allowed is 1000 items'
            session_query = session_query.filter(filter['field'].in_(value))
    return session_query


def get_list_query_filter_datetime_from(session_query, filters, filter):
    if filter['value'] is not None:
        session_query = session_query.filter(filter['field'] >= filter['value'])
    return session_query


def get_list_query_filter_datetime_to(session_query, filters, filter):
    if filter['value'] is not None:
        session_query = session_query.filter(filter['field'] <= filter['value'])
    return session_query


def get_list_query_filter_prefix(session_query, filters, filter):
    if filter['value'] is not None:
        session_query = session_query.filter(filter['field'].like('{}%'.format(filter['value'])))
    return session_query


def get_list_query_filter_contains(session_query, filters, filter):
    if filter['value'] is not None:
        session_query = session_query.filter(filter['field'].like('%{}%'.format(filter['value'])))
    return session_query


def get_list_query_filter_date_in_range(session_query, filters, filter):
    if filter['value'] is not None:
        min_field, max_field = filter['fields']
        session_query = session_query.filter(filter['value'] >= min_field, filter['value'] <= max_field)
    return session_query


def get_item(db_model, field, value):
    with get_session() as session:
        return session.query(db_model).filter(field == value).one().__dict__


class PydanticRelatedModel():

    def __init__(self, field_name_prefix, pydantic_model, exclude_field_names=None, include_field_names=None):
        self.field_name_prefix = field_name_prefix
        self.pydantic_model = pydantic_model
        self.exclude_field_names = exclude_field_names
        self.include_field_names = include_field_names

    def update_create_model_kwargs(self, kwargs):
        for name, field in self.pydantic_model.__fields__.items():
            if self.include_field_names and name not in self.include_field_names:
                continue
            if self.exclude_field_names and name in self.exclude_field_names:
                continue
            default = field.default
            if default is ...:
                default = None
            kwargs['{}{}'.format(self.field_name_prefix, name)] = (field.type_, default)

    def add_orm_obj_to_dict_res(self, orm_obj, res):
        if orm_obj:
            for name in self.pydantic_model.__fields__.keys():
                if self.exclude_field_names and name in self.exclude_field_names:
                    continue
                res['{}{}'.format(self.field_name_prefix, name)] = getattr(orm_obj, name)


def pydantic_create_model_with_related(model_name, base_model, *related_models):
    kwargs = {}
    for name, field in base_model.__fields__.items():
        kwargs[name] = (field.type_, field.default)
    for related_model in related_models:
        related_model.update_create_model_kwargs(kwargs)
    return pydantic.create_model(model_name, **kwargs)


def param_limit(max_limit=100):
    return fastapi.Query(None, description=f'Limit the number of results up to {max_limit}. If not specified will limit to {max_limit} results. Use the offset param to get more results.')


def param_offset():
    return fastapi.Query(None, description='Item number to start returning results from.')


def param_filter_list(what_singular, example='1,2,3'):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Comma-separated list of values, e.g. "{example}".')


def param_filter_prefix(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular} prefix. Only return items which start with given string.')


def param_filter_equals(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Only return items which exactly match given string.')


def param_filter_contains(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Only return items which contain given string.')


def param_filter_datetime_from(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Only return items which have date/time after or equals to given value. Format: "YYYY-MM-DDTHH:MM:SS+Z", e.g. "2021-11-03T55:48:49+02:00". '
                                           f'Note that all date/times must have a timezone specification.')


def param_filter_datetime_to(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Only return items which have date/time before or equals to given value. Format: "YYYY-MM-DDTHH:MM:SS+Z", e.g. "2021-11-03T55:48:49+02:00". '
                                           f'Note that all date/times must have a timezone specification.')


def param_filter_date_from(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Only return items which have a date after or equals to given value. Format: "YYYY-MM-DD", e.g. "2021-11-03".')


def param_filter_date_to(what_singular):
    return fastapi.Query(None, description=f'Filter by {what_singular}. Only return items which have a date before or equals to given value. Format: "YYYY-MM-DD", e.g. "2021-11-03".')


def param_order_by(example='field_one asc,field_two desc'):
    return fastapi.Query(None, description=f'Order of the results. Comma-separated list of fields and direction, e.g.: "{example}"')


def router_list(router, tag, pydantic_model, what_plural):
    return router.get("/list", tags=[tag], response_model=typing.List[pydantic_model], description=f'List of {what_plural}.')


def router_get(router, tag, pydantic_model, what_singular):
    return router.get('/get', tags=[tag], response_model=pydantic_model,
                      description=f'Return a single {what_singular} based on id')


def param_get_id(what_singular):
    return fastapi.Query(..., description=f'{what_singular} id to get')
