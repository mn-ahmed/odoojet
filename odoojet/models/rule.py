
import copy
from lxml import etree

from odoo import _, api, fields, models, modules
from odoo.exceptions import UserError

FIELDS_BLACKLIST = [
    "id",
    "create_uid",
    "create_date",
    "write_uid",
    "write_date",
    "display_name",
    "__last_update",
]
# Used for performance, to avoid a dictionary instanciation when we need an
# empty dict to simplify algorithms
EMPTY_DICT = {}


class DictDiffer(object):
    """Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """

    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current = set(current_dict)
        self.set_past = set(past_dict)
        self.intersect = self.set_current.intersection(self.set_past)

    def added(self):
        return self.set_current - self.intersect

    def removed(self):
        return self.set_past - self.intersect

    def changed(self):
        return {o for o in self.intersect if self.past_dict[o] != self.current_dict[o]}

    def unchanged(self):
        return {o for o in self.intersect if self.past_dict[o] == self.current_dict[o]}


class odoojetRule(models.Model):
    _name = "odoojet.rule"
    _description = "odoojet - Rule"

    name = fields.Char(required=True)
    model_id = fields.Many2one(
        "ir.model",
        "Model",
        help="Select model for which you want to generate log.",
    )

    btn_id = fields.Many2one('buttons.nodes', string='Button',
                                                 domain="[('node_option','=','button')]")

    btn_name = fields.Char(string='Button Name', related='btn_id.attribute_name', readonly=True, store=True)

    model_name = fields.Char(string='Model Name', related='model_id.model', readonly=True, store=True)
    model_model = fields.Char(string="Technical Model Name", readonly=True)
    user_ids = fields.Many2many(
        "res.users",
        "audittail_rules_users",
        "user_id",
        "rule_id",
        string="Users",
        help="if  User is not added then it will applicable for all users",
        
    )
    log_read = fields.Boolean(
        "Log Reads",
        default=False,
        help=(
            "Select this if you want to keep track of read/open on any "
            "record of the model of this rule"
        ),
        
    )
    log_write = fields.Boolean(
        "Log Writes",
        default=False,
        help=(
            "Select this if you want to keep track of modification on any "
            "record of the model of this rule"
        ),
        
    )
    log_unlink = fields.Boolean(
        "Log Deletes",
        default=False,
        help=(
            "Select this if you want to keep track of deletion on any "
            "record of the model of this rule"
        ),
        
    )

    log_archive = fields.Boolean(
        "Log archive",
        default=False,
        help=(
            "Select this if you want to keep track of archive on any "
            "record of the model of this rule"
        ),
        
    )

    log_unarchive = fields.Boolean(
        "Log unarchive",
        default=False,
        help=(
            "Select this if you want to keep track of archive on any "
            "record of the model of this rule"
        ),

    )
    
    log_export = fields.Boolean(
        "Log export",
        default=False,
        help=(
            "Select this if you want to keep track of export on any "
            "record of the model of this rule"
        ),
    )

    log_create = fields.Boolean(
        "Log Creates",
        default=False,
        help=(
            "Select this if you want to keep track of creation on any "
            "record of the model of this rule"
        ),
        
    )


    fields_to_track_ids = fields.Many2many(
        "ir.model.fields",
        domain="[('model_id', '=', model_id)]",
        string="Fields to track",
        
    )

    fields_to_exclude_ids = fields.Many2one(
        "ir.model.fields",
        string="Fields to exclude",

    )

    btn_id_hide = fields.Boolean("hide",  default=False,)

    # _sql_constraints = [
    #     (
    #         "model_uniq",
    #         "unique(model_id)",
    #         (
    #             "There is already a rule defined on this model\n"
    #             "You cannot define another: please edit the existing one."
    #         ),
    #     )
    # ]

    @api.onchange('btn_id')
    def _onchange_btn_id(self):
        if self.btn_id:
            self.btn_id_hide = True
            self.log_read = False
            self.log_write = False
            self.log_create = False
            self.log_export = False
            self.log_archive = False
            self.log_unarchive = False
            self.log_unlink = False
        else:
            self.btn_id_hide = False


    def _store_btn_data(self, btn, smart_button=False, smart_button_string=False):
        # string_value is used in case of kanban view button store,
        string_value = 'string_value' in self._context.keys() and self._context['string_value'] or False

        store_model_button_obj = self.env['buttons.nodes']
        name = btn.get('string') or string_value
        if smart_button:
            name = smart_button_string
        store_model_button_obj.create({
            'model_id': self.model_id.id,
            'node_option': 'button',
            'attribute_name': btn.get('name'),
            'attribute_string': name,
            'button_type': btn.get('type'),
            'is_smart_button': smart_button,
        })

    @api.model
    @api.onchange('model_id')
    def _get_button(self):
        store_model_nodes_obj = self.env['buttons.nodes']
        view_obj = self.env['ir.ui.view']

        if self.model_id and self.model_name:

            view_list = ['form']
            for view in view_list:
                for views in view_obj.search(
                        [('model', '=', self.model_name), ('type', '=', view), ('inherit_id', '=', False)]):
                    res = self.env[self.model_name].sudo().fields_view_get(view_id=views.id, view_type=view)
                    doc = etree.XML(res['arch'])

                    object_link = doc.xpath("//a")
                    for btn in object_link:
                        if btn.text and '\n' not in btn.text and 'type' in btn.attrib.keys() and btn.attrib[
                            'type'] and 'name' in btn.attrib.keys() and btn.attrib['name']:
                            domain = [('button_type', '=', btn.get('type')), ('attribute_string', '=', btn.text),
                                      ('attribute_name', '=', btn.get('name')), ('model_id', '=', self.model_id.id),
                                      ('node_option', '=', 'link')]
                            if not store_model_nodes_obj.search(domain):
                                store_model_nodes_obj.create({
                                    'model_id': self.model_id.id,
                                    'node_option': 'link',
                                    'attribute_name': btn.get('name'),
                                    'attribute_string': btn.text,
                                    'button_type': btn.get('type'),
                                })

                    object_button = doc.xpath("//button[@type='object']")
                    for btn in object_button:
                        string_value = btn.get('string')
                        if not string_value:
                            string_value = btn.get('name')
                        if btn.get('name') and string_value:
                            domain = [('button_type', '=', btn.get('type')), ('attribute_string', '=', string_value),
                                      ('attribute_name', '=', btn.get('name')), ('model_id', '=', self.model_id.id),
                                      ('node_option', '=', 'button')]
                            if not store_model_nodes_obj.search(domain):
                                self.with_context(string_value=string_value)._store_btn_data(btn)

                    action_button = doc.xpath("//button[@type='action']")
                    for btn in action_button:
                        string_value = btn.get('string')
                        if btn.get('name') and string_value:
                            domain = [('button_type', '=', btn.get('type')), ('attribute_string', '=', string_value),
                                      ('attribute_name', '=', btn.get('name')), ('model_id', '=', self.model_id.id),
                                      ('node_option', '=', 'button')]
                            if not store_model_nodes_obj.search(domain):
                                self.with_context(string_value=string_value)._store_btn_data(btn)

    def _register_hook(self):
        """Get all rules and apply them to log method calls."""
        super(odoojetRule, self)._register_hook()
        if not hasattr(self.pool, "_odoojet_field_cache"):
            self.pool._odoojet_field_cache = {}
        if not hasattr(self.pool, "_odoojet_model_cache"):
            self.pool._odoojet_model_cache = {}
        if "base_import.import" in self.pool._odoojet_model_cache:
            self.pool._odoojet_model_cache.update({
                "base_import.import":9999
            })

        return self._patch_methods()

    def _patch_methods(self):
        """Patch ORM methods of models defined in rules to log their calls."""
        updated = False
        model_cache = self.pool._odoojet_model_cache
        for rule in self:
            model_cache[rule.model_id.model] = rule.model_id.id
            model_model = self.env[rule.model_id.model or rule.model_model]
            # CRUD
            #   -> create
            check_attr = "odoojet_ruled_create"
            if rule.log_create and not hasattr(model_model, check_attr):
                model_model._patch_method("create", rule._make_create())
                setattr(type(model_model), check_attr, True)
                updated = True
            #   -> read
            check_attr = "odoojet_ruled_read"
            if rule.log_read and not hasattr(model_model, check_attr):
                model_model._patch_method("read", rule._make_read())
                setattr(type(model_model), check_attr, True)
                updated = True
            #   -> write
            check_attr = "odoojet_ruled_write"
            if rule.log_write and not hasattr(model_model, check_attr):
                model_model._patch_method("write", rule._make_write())
                setattr(type(model_model), check_attr, True)
                updated = True
            #   -> unlink
            check_attr = "odoojet_ruled_unlink"
            if rule.log_unlink and not hasattr(model_model, check_attr):
                model_model._patch_method("unlink", rule._make_unlink())
                setattr(type(model_model), check_attr, True)
                updated = True

            check_attr = "odoojet_ruled_archive"
            if rule.log_archive and not hasattr(model_model, check_attr):
                model_model._patch_method("action_archive", rule._make_archive())
                setattr(type(model_model), check_attr, True)
                updated = True

            check_attr = "odoojet_ruled_unarchive"
            if rule.log_unarchive and not hasattr(model_model, check_attr):
                model_model._patch_method("action_unarchive", rule._make_unarchive())
                setattr(type(model_model), check_attr, True)
                updated = True

            check_attr = "odoojet_ruled_export"
            if rule.log_export and not hasattr(model_model, check_attr):
                model_model._patch_method("export_data", rule._make_export())
                setattr(type(model_model), check_attr, True)
                updated = True



        return updated

    def _revert_methods(self):
        """Restore original ORM methods of models defined in rules."""
        updated = False
        for rule in self:
            model_model = self.env[rule.model_id.model or rule.model_model]
            for method in ["create", "read", "write", "unlink"]:
                if getattr(rule, "log_%s" % method) and hasattr(
                    getattr(model_model, method), "origin"
                ):
                    model_model._revert_method(method)
                    delattr(type(model_model), "odoojet_ruled_%s" % method)
                    updated = True
        if updated:
            modules.registry.Registry(self.env.cr.dbname).signal_changes()

    @api.model
    def create(self, vals):
        """Update the registry when a new rule is created."""
        if "model_id" not in vals or not vals["model_id"]:
            raise UserError(_("No model defined to create line."))
        model = self.env["ir.model"].sudo().browse(vals["model_id"])
        vals.update({"model_name": model.name, "model_model": model.model})
        new_record = super().create(vals)
        if new_record._register_hook():
            modules.registry.Registry(self.env.cr.dbname).signal_changes()
        return new_record

    def write(self, vals):
        """Update the registry when existing rules are updated."""
        if "model_id" in vals:
            if not vals["model_id"]:
                raise UserError(_("Field 'model_id' cannot be empty."))
            model = self.env["ir.model"].sudo().browse(vals["model_id"])
            vals.update({"model_name": model.name, "model_model": model.model})
        res = super().write(vals)
        if self._register_hook():
            modules.registry.Registry(self.env.cr.dbname).signal_changes()
        return res

    def unlink(self):
        """ rules before removing them."""
        return super(odoojetRule, self).unlink()

    @api.model
    def get_odoojet_fields(self, model):
        """
        Get the list of odoojet fields for a model
        By default it is all stored fields only, but you can
        override this.
        """
        return list(
            n
            for n, f in model._fields.items()
            if (not f.compute and not f.related) or f.store
        )

    def _make_create(self):
        """Instanciate a create method that log its calls."""
        self.ensure_one()

        @api.model_create_multi
        @api.returns("self", lambda value: value.id)
        def create_fast(self, vals_list, **kwargs):
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            vals_list2 = copy.deepcopy(vals_list)
            new_records = create_fast.origin(self, vals_list, **kwargs)
            new_values = {}
            for vals, new_record in zip(vals_list2, new_records):
                new_values.setdefault(new_record.id, vals)
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                new_records.ids,
                "create",
                None,
                new_values,
            )
            return new_records

        return create_fast

    def _make_read(self):
        """Instanciate a read method that log its calls."""
        self.ensure_one()

        def read(self, fields=None, load="_classic_read", **kwargs):
            result = read.origin(self, fields, load, **kwargs)
            # Sometimes the result is not a list but a dictionary
            # Also, we can not modify the current result as it will break calls
            result2 = result
            if not isinstance(result2, list):
                result2 = [result]
            read_values = {d["id"]: d for d in result2}
            # Old API

            # If the call came from odoojet itself, skip logging:
            # avoid logs on `read` produced by odoojet during internal
            # processing: read data of relevant records, 'ir.model',
            # 'ir.model.fields'... (no interest in logging such operations)
            if self.env.context.get("odoojet_disabled"):
                return result
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "read",
                read_values,
                None,
            )
            return result

        return read

    def _make_archive(self):
        """Instanciate a write method that log its calls."""

        self.ensure_one()

        def action_archive(self, **kwargs):
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            fields_list = rule_model.get_odoojet_fields(self)
            old_values = {
                d["id"]: d
                for d in self.sudo()
                .with_context(prefetch_fields=False)
                .read(fields_list)
            }
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "archive",
                old_values,
                None,
            )
            return action_archive.origin(self, **kwargs)


        return action_archive

    def _make_unarchive(self):
        """Instanciate a write method that log its calls."""

        self.ensure_one()
        def action_unarchive(self, **kwargs):
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            fields_list = rule_model.get_odoojet_fields(self)
            old_values = {
                d["id"]: d
                for d in self.sudo()
                .with_context(prefetch_fields=False)
                .read(fields_list)
            }
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "unarchive",
                old_values,
                None,
            )
            return action_unarchive.origin(self, **kwargs)


        return action_unarchive


    def _make_export(self):
        """Instanciate a write method that log its calls."""

        self.ensure_one()
        def export_data(self, fields_to_export):
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            old_values = {
                d["id"]: d
                for d in self.sudo()
                .with_context(prefetch_fields=False)
                .read(fields_to_export)
            }
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "export",
                old_values,
                None,
            )
            return export_data.origin(self, fields_to_export)

        return export_data

    def _make_write(self):
        """Instanciate a write method that log its calls."""
        self.ensure_one()

        def write_fast(self, vals, **kwargs):
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            # Log the user input only, no matter if the `vals` is updated
            # afterwards as it could not represent the real state
            # of the data in the database
            vals2 = dict(vals)
            old_vals2 = dict.fromkeys(list(vals2.keys()), False)
            old_values = {id_: old_vals2 for id_ in self.ids}
            new_values = {id_: vals2 for id_ in self.ids}
            result = write_fast.origin(self, vals, **kwargs)

            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "write",
                old_values,
                new_values,
            )
            return result

        return write_fast

    def _make_unlink(self):
        """Instanciate an unlink method that log its calls."""
        self.ensure_one()

        def unlink_fast(self, **kwargs):
            self = self.with_context(odoojet_disabled=True)
            rule_model = self.env["odoojet.rule"]
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "unlink",
                None,
                None,
            )
            return unlink_fast.origin(self, **kwargs)

        return unlink_fast

    def create_logs(
        self,
        uid,
        res_model,
        res_ids,
        method,
        old_values=None,
        new_values=None,
    ):
        """Create logs. `old_values` and `new_values` are dictionaries, e.g:
        {RES_ID: {'FIELD': VALUE, ...}}
        """
        if old_values is None:
            old_values = EMPTY_DICT
        if new_values is None:
            new_values = EMPTY_DICT
        log_model = self.env["odoojet.log"]
        http_request_model = self.env["odoojet.http.request"]
        http_session_model = self.env["odoojet.http.session"]

        model_model = self.env[res_model]
        model_id = self.pool._odoojet_model_cache[res_model]
        odoojet_rule = self.env["odoojet.rule"].search([("model_id", "=", model_id)])
        fields_to_track = odoojet_rule.fields_to_track_ids.mapped("name")
        for res_id in res_ids:
            if model_model.browse(res_id).name_get():
                name = model_model.browse(res_id).name_get()
                res_name = name and name[0] and name[0][1]
            else:
                res_name = method
            vals = {
                "name": res_name,
                "model_id": model_id,
                "res_id": res_id,
                "method": method,
                "user_id": uid,
                "http_request_id": http_request_model.current_http_request(),
                "http_session_id": http_session_model.current_http_session(),
            }
            log = log_model.create(vals)
            diff = DictDiffer(
                new_values.get(res_id, EMPTY_DICT), old_values.get(res_id, EMPTY_DICT)
            )
            if method == "create":
                self._create_log_line_on_create(
                    log, diff.added(), new_values, fields_to_track
                )
            elif method == "read":
                self._create_log_line_on_read(
                    log,
                    list(old_values.get(res_id, EMPTY_DICT).keys()),
                    old_values,
                    fields_to_track,
                )
            elif method == "write":
                self._create_log_line_on_write(
                    log, diff.changed(), old_values, new_values, fields_to_track
                )


    def _get_field(self, model, field_name):
        cache = self.pool._odoojet_field_cache
        if field_name not in cache.get(model.model, {}):
            cache.setdefault(model.model, {})
            # - we use 'search()' then 'read()' instead of the 'search_read()'
            #   to take advantage of the 'classic_write' loading
            # - search the field in the current model and those it inherits
            field_model = self.env["ir.model.fields"].sudo()
            all_model_ids = [model.id]
            all_model_ids.extend(model.inherited_model_ids.ids)
            field = field_model.search(
                [("model_id", "in", all_model_ids), ("name", "=", field_name)]
            )
            # The field can be a dummy one, like 'in_group_X' on 'res.users'
            # As such we can't log it (field_id is required to create a log)
            if not field:
                cache[model.model][field_name] = False
            else:
                field_data = field.read(load="_classic_write")[0]
                cache[model.model][field_name] = field_data
        return cache[model.model][field_name]

    def _create_log_line_on_read(
        self, log, fields_list, read_values, fields_to_track
    ):
        """Log field filled on a 'read' operation."""
        log_line_model = self.env["odoojet.log.line"]
        for field_name in fields_list:
            if field_name not in fields_to_track or field_name in FIELDS_BLACKLIST:
                continue
            field = self._get_field(log.model_id, field_name)
            # not all fields have an ir.models.field entry (ie. related fields)
            if field:
                log_vals = self._prepare_log_line_vals_on_read(log, field, read_values)
                log_line_model.create(log_vals)

    def _prepare_log_line_vals_on_read(self, log, field, read_values):
        """Prepare the dictionary of values used to create a log line on a
        'read' operation.
        """
        vals = {
            "field_id": field["id"],
            "log_id": log.id,
            "old_value": read_values[log.res_id][field["name"]],
            "old_value_text": read_values[log.res_id][field["name"]],
            "new_value": False,
            "new_value_text": False,
        }
        if field["relation"] and "2many" in field["ttype"]:
            old_value_text = (
                self.env[field["relation"]].browse(vals["old_value"]).name_get()
            )
            vals["old_value_text"] = old_value_text
        return vals

    def _create_log_line_on_write(
        self, log, fields_list, old_values, new_values, fields_to_track
    ):
        """Log field updated on a 'write' operation."""
        log_line_model = self.env["odoojet.log.line"]
        for field_name in fields_list:
            if field_name not in fields_to_track or field_name in FIELDS_BLACKLIST:
                continue
            field = self._get_field(log.model_id, field_name)
            # not all fields have an ir.models.field entry (ie. related fields)
            if field:
                log_vals = self._prepare_log_line_vals_on_write(
                    log, field, old_values, new_values
                )
                log_line_model.create(log_vals)

    def _prepare_log_line_vals_on_write(self, log, field, old_values, new_values):
        """Prepare the dictionary of values used to create a log line on a
        'write' operation.
        """
        vals = {
            "field_id": field["id"],
            "log_id": log.id,
            "old_value": old_values[log.res_id][field["name"]],
            "old_value_text": old_values[log.res_id][field["name"]],
            "new_value": new_values[log.res_id][field["name"]],
            "new_value_text": new_values[log.res_id][field["name"]],
        }
        # for *2many fields, log the name_get
        return vals

    def _create_log_line_on_create(
        self, log, fields_list, new_values, fields_to_track
    ):
        """Log field filled on a 'create' operation."""
        log_line_model = self.env["odoojet.log.line"]
        for field_name in fields_list:
            if field_name not in fields_to_track or field_name in FIELDS_BLACKLIST:
                continue
            field = self._get_field(log.model_id, field_name)
            # not all fields have an ir.models.field entry (ie. related fields)
            if field:
                log_vals = self._prepare_log_line_vals_on_create(log, field, new_values)
                log_line_model.create(log_vals)

    def _prepare_log_line_vals_on_create(self, log, field, new_values):
        """Prepare the dictionary of values used to create a log line on a
        'create' operation.
        """
        vals = {
            "field_id": field["id"],
            "log_id": log.id,
            "old_value": False,
            "old_value_text": False,
            "new_value": new_values[log.res_id][field["name"]],
            "new_value_text": new_values[log.res_id][field["name"]],
        }

        return vals



class LogsImport(models.TransientModel):
    _inherit = 'base_import.import'

    def execute_import(self, fields, columns, options, dryrun=False):
        res = super(LogsImport, self).execute_import(fields, columns, options, dryrun=False)
        if res.ids:
            rule_model = self.env["odoojet.rule"]
            rule_model.sudo().create_logs(
                self.env.uid,
                self._name,
                self.ids,
                "Import %s" %self.res_model,
                None,
                None,
            )
        return res
