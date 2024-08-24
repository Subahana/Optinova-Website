# import environ

# env = environ.Env()
# environ.Env.read_env()  # reads .env file


# # Quick-start development settings - unsuitable for production
# SECRET_KEY = env('DJANGO_SECRET_KEY', default='django-insecure-r$zpyql!27jw*1tsvbv&z_9*sje6fbz=p-1(7q^=1ekzsy)058')

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'optinova_project',
#         'USER': env('POSTGRES_USER', default='postgres'),
#         'PASSWORD': env('POSTGRES_PASSWORD', default='9446265404'),
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }

# # Email configuration

# EMAIL_HOST_USER = 'subahanasulfikar@gmail.com'
# EMAIL_HOST_PASSWORD = 'ggyo snmi omeq nuut'
# DEFAULT_FROM_EMAIL = 'subahanasulfikar@gmail.com'

# # Google SSO settings
# SOCIALACCOUNT_PROVIDERS = {
#     'google': {
#         'SCOPE': [
#             'profile',
#             'email',
#         ],
#         'AUTH_PARAMS': {
#             'access_type': 'online',
#         },
#         'OAUTH_CLIENT_ID': '1047587046982-rb8s3mbf667tgbgqqt5ai6lcrft9500c.apps.googleusercontent.com',
#         'OAUTH_CLIENT_SECRET': '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',
#         'REDIRECT_URI': 'http://127.0.0.1:8000/accounts/google/callback/',  # Ensure this is correct
#     }
# }
