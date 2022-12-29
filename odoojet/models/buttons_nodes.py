from odoo import fields, models

class buttons_nodes(models.Model):
    _name = 'buttons.nodes'
    _description = 'Buttons Nodes'
    _rec_name = 'attribute_string'

    model_id = fields.Many2one('ir.model', string='Model', index=True, ondelete='cascade', required=True)
    node_option = fields.Selection([('button', 'Button'), ('page', 'Page'), ('link', 'Link')], string="Node Option",
                                   required=True)
    attribute_name = fields.Char('Attribute Name')
    attribute_string = fields.Char('Attribute String', required=True)

    button_type = fields.Selection([('object', 'Object'), ('action', 'Action')], string="Button Type")
    is_smart_button = fields.Boolean('Smart Button')

    def name_get(self):
        result = []
        for rec in self:
            name = rec.attribute_string
            if rec.attribute_name:
                name = name + ' (' + rec.attribute_name + ')'
                if rec.is_smart_button and rec.node_option == 'button':
                    name = name + ' (Smart Button)'
            result.append((rec.id, name))
        return result
