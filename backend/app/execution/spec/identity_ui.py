"""Shared versioned selectors, available before source generation."""
def ui_manifest():
    return {'version':1,'routes':['/account','/account/reset','/admin'],
        'ids':{'email':'identity-email','password':'identity-password','submit':'identity-submit',
            'message':'identity-message','address':'identity-address','admin':'identity-admin'}}
