from marshmallow import Schema, fields, validate

class LoginSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    password = fields.Str(required=True, validate=validate.Length(min=6))

class RegisterSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=80))
    password = fields.Str(required=True, validate=validate.Length(min=6))
    user_type = fields.Str(required=True, validate=validate.OneOf(["teacher", "student"]))
    name = fields.Str(required=True, validate=validate.Length(min=3))
    course = fields.Str(required=True, validate=validate.Length(min=3))
    group = fields.Int(missing=1)
    
class UserDataUpdateSchema(Schema):
    old_password = fields.Str(validate=validate.Length(min=6))
    new_password = fields.Str(validate=validate.Length(min=6))

