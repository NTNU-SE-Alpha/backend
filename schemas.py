from marshmallow import Schema, fields, validate

class LoginSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    password = fields.Str(required=True, validate=validate.Length(min=6))
    
class UserDataUpdateSchema(Schema):
    password = fields.Str(validate=validate.Length(min=6))

