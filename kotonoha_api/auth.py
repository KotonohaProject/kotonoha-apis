import requests
from kotonoha_api.firebase_utils import db

def get_user_data(access_token):
    """
    {
        id: '108493981573305913629',
        email: 'shinnosuke.uesaka@gmail.com',
        verified_email: true,
        name: 'Shinnosuke Uesaka',
        given_name: 'Shinnosuke',
        family_name: 'Uesaka',
        picture: 'https://lh3.googleusercontent.com/a/ACg8ocIyMqtMnbxkIbZ6dMqbWYQUqMeQwkD2Nl7MYPEZdTdTUpOx=s96-c',
        locale: 'en-US'
    }
    """
    url = 'https://www.googleapis.com/oauth2/v1/userinfo'
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    res = requests.get(url, headers=headers)
    return res.json()

def get_user_collection(access_token):
    email = get_user_data(access_token)['email']
    # search for user where email field is equal to email
    users = db.collection('users').where('email', '==', email).get() # before doing .get(), it's a Query object
    if len(users) == 0:
        raise Exception('User not found')
    elif len(users) > 1:
        raise Exception('Multiple users found')
    else:
        return users[0] # this is a DocumentSnapshot
