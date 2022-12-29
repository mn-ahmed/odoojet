
{
    "name": "Dynamic Odoo Logs | User Activity Audit",
    "version": "15.0.0",
    'summary': """
        Module Dynamic Odoo Logs help you to make own configuration to actions and evry function in odoo""",

    'description': """
        Dynamic Odoo Logs is a powerful tool that helps you keep track of all the activity 
        in your Odoo system. 
        With this feature, you can easily see which users are performing which actions, 
        when they are taking place, and which objects are being modified.
    """,
    "author": "medconsultantweb@gmail.com",
    'price': 85,
    'license': 'OPL-1',
    'currency': 'EUR',
    "category": "Tools",
    "depends": ["base", "account", "purchase", "stock", "sale"],
    'images': ['static/description/main.png'],

    "data": [
        "demo/demo.xml",
        "security/ir.model.access.csv",
        "views/odoojet_view.xml",
        "views/http_session_view.xml",
        "views/http_request_view.xml",
        "views/buttons_nodes_view.xml",
    ],
    "application": True,
    "installable": True,
}
