from skyland import generate_signature

# s = '/api/v1/user/check'
s = '/api/v1/user/me'
token = '11173b53e138d291c440e347107cc5b4'
r = generate_signature(token, s, '', )
